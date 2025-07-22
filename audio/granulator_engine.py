# GranulatorApp/audio/granulator_engine.py

import numpy as np
from scipy.signal.windows import hann  # For applying a window to grains
import librosa.effects  # For pitch shifting (if you uncomment it later)
import threading
import time  # For potential timing in grain generation

# Import constants for default values
from utils.constants import DEFAULT_GRAIN_LENGTH_MS, DEFAULT_GRAIN_DENSITY, DEFAULT_SAMPLE_RATE, AUDIO_BUFFER_SIZE


class GranulatorEngine:  # ONLY ONE CLASS DEFINITION HERE
    """
    The core engine for granular synthesis.
    It takes source audio, applies granulation parameters, and generates
    audio buffers for real-time playback.
    """

    def __init__(self, audio_data: np.ndarray | None = None, sample_rate: int = DEFAULT_SAMPLE_RATE):
        """
        Initializes the GranulatorEngine.

        Args:
            audio_data (np.ndarray | None): The initial source audio data.
            sample_rate (int): The sample rate of the audio data.
        """
        self._audio_data = audio_data
        self._sample_rate = sample_rate
        # Store total audio samples for percentage calculations
        self._total_audio_samples = 0
        if audio_data is not None:
            self._total_audio_samples = len(audio_data)

        # Granulation parameters (initialized with defaults)
        self._grain_length_percentage = 50  # Now percentage (0-100)
        self._grain_density = DEFAULT_GRAIN_DENSITY  # grains per second
        self._pitch_shift_semitones = 0.0  # in semitones
        self._overlap_ratio = 0.5  # overlap between grains (0.0 to 1.0)

        # Conceptual playhead position for the granulation engine.
        self._current_loop_playhead_position = 0

        self._start_position_percentage = 0  # Start position from 0-100%
        self._start_position_sample = 0  # Calculated start position in samples

        # List to hold currently active grains
        self._active_grains = []

        # Lock for thread-safe access to active_grains and playhead_position
        self._lock = threading.Lock()

        print(
            f"GranulatorEngine initialized. Default grain length: {self._grain_length_percentage}%, Density: {self._grain_density}gps")

    def set_audio_source(self, audio_data: np.ndarray, sample_rate: int):
        """
        Sets or updates the source audio for the granulator.
        Resets the playhead and clears active grains.
        """
        with self._lock:
            self._audio_data = audio_data
            self._sample_rate = sample_rate
            self._total_audio_samples = len(audio_data) if audio_data is not None else 0

            self._active_grains = []
            self._calculate_start_position_sample()

            self._current_loop_playhead_position = 0

            if self._audio_data is not None:
                print(
                    f"GranulatorEngine: Audio source updated. Length: {self._total_audio_samples / sample_rate:.2f}s, SR: {sample_rate}Hz")
            else:
                print("GranulatorEngine: Audio source cleared.")

    def set_grain_length_percentage(self, percentage: int):
        """Sets the grain length as a percentage of the total audio length."""
        with self._lock:
            self._grain_length_percentage = max(1, min(100, percentage))
            print(f"GranulatorEngine: Grain length set to {self._grain_length_percentage}%")

    def set_grain_density(self, density: int):
        """Sets the grain density in grains per second."""
        with self._lock:
            self._grain_density = max(1, density)
            print(f"GranulatorEngine: Grain density set to {self._grain_density} grains/s")

    def set_pitch_shift(self, semitones: float):
        """Sets the pitch shift in semitones."""
        with self._lock:
            self._pitch_shift_semitones = semitones
            print(f"GranulatorEngine: Pitch shift set to {self._pitch_shift_semitones:.1f} semitones")

    def set_start_position_percentage(self, percentage: int):
        """
        Sets the start position for granulation as a percentage of the audio length.
        """
        with self._lock:
            self._start_position_percentage = max(0, min(100, percentage))
            self._calculate_start_position_sample()
            self._current_loop_playhead_position = 0
            print(f"GranulatorEngine: Start Position set to {self._start_position_percentage}%")

    def _calculate_start_position_sample(self):
        """
        Calculates the start position in samples based on the percentage
        and the current audio data length.
        """
        if self._audio_data is not None and self._total_audio_samples > 0:
            self._start_position_sample = int(self._total_audio_samples * (self._start_position_percentage / 100.0))
            self._start_position_sample = min(self._start_position_sample, self._total_audio_samples - 1)
            self._start_position_sample = max(0, self._start_position_sample)
        else:
            self._start_position_sample = 0

    def get_current_loop_region(self) -> tuple[int, int]:
        """
        Returns the current start and end of the conceptual granulation loop region in SAMPLES.
        """
        if self._audio_data is None or self._sample_rate <= 0 or self._total_audio_samples == 0:
            return 0, 0

        with self._lock:
            loop_start_sample = self._start_position_sample
            loop_length_samples = int(self._total_audio_samples * (self._grain_length_percentage / 100.0))
            if loop_length_samples <= 0: loop_length_samples = 1

            loop_end_sample = min(loop_start_sample + loop_length_samples, self._total_audio_samples)

            return loop_start_sample, loop_end_sample

    def generate_audio_buffer(self, num_frames: int) -> np.ndarray:
        """
        Generates a buffer of granulated audio. This method is called repeatedly
        by the AudioPlayer to get audio data.
        """
        # Minimize lock: copy all parameters needed
        with self._lock:
            audio_data = self._audio_data
            sample_rate = self._sample_rate
            total_audio_samples = self._total_audio_samples
            grain_length_percentage = self._grain_length_percentage
            grain_density = self._grain_density
            start_position_sample = self._start_position_sample
            current_loop_playhead_position = self._current_loop_playhead_position
            start_position_percentage = self._start_position_percentage
            # Copy active grains for modification
            active_grains = list(self._active_grains)

        if audio_data is None or sample_rate <= 0 or total_audio_samples == 0:
            return np.zeros(num_frames, dtype=np.float32)

        output_buffer = np.zeros(num_frames, dtype=np.float32)

        audio_length = total_audio_samples

        grain_length_samples = int(audio_length * (grain_length_percentage / 100.0))
        if grain_length_samples <= 0:
            grain_length_samples = 1

        # Calculate loop start/end region
        loop_start_sample_actual = start_position_sample
        loop_length_samples = int(total_audio_samples * (grain_length_percentage / 100.0))
        if loop_length_samples <= 0:
            loop_length_samples = 1
        loop_end_sample_actual = min(loop_start_sample_actual + loop_length_samples, total_audio_samples)
        loop_duration_samples = loop_end_sample_actual - loop_start_sample_actual
        if loop_duration_samples <= 0:
            loop_duration_samples = 1

        if grain_density <= 0:
            grains_to_trigger = 0
        else:
            grains_to_trigger = int(grain_density * (num_frames / sample_rate))
            if grains_to_trigger == 0 and (sample_rate / grain_density) <= num_frames:
                grains_to_trigger = 1

        # Advance playhead
        current_loop_playhead_position = (current_loop_playhead_position + num_frames)
        if loop_duration_samples > 0:
            current_loop_playhead_position %= loop_duration_samples
        else:
            current_loop_playhead_position = 0

        # Grain triggering
        for _ in range(grains_to_trigger):
            grain_base_start_idx_in_loop = current_loop_playhead_position

            deviation_range_samples = int(grain_length_samples * 0.5)
            deviation_range_samples = max(0, deviation_range_samples)

            if deviation_range_samples == 0:
                random_deviation = 0
            else:
                random_deviation = np.random.randint(-deviation_range_samples, deviation_range_samples + 1)

            grain_source_start_idx = loop_start_sample_actual + grain_base_start_idx_in_loop + random_deviation
            indices = np.arange(grain_source_start_idx, grain_source_start_idx + grain_length_samples, dtype=int)
            grain_raw = np.take(audio_data, indices, mode='wrap')
            window = hann(len(grain_raw))
            windowed_grain = grain_raw * window

            # Apply pitch shift if necessary (re-enable if desired later)
            # if self._pitch_shift_semitones != 0.0:
            #    try:
            #        windowed_grain_float = windowed_grain.astype(np.float32)
            #        if windowed_grain_float.size == 0 or sample_rate <= 0:
            #            pitched_grain = windowed_grain_float
            #        else:
            #            pitched_grain = librosa.effects.pitch_shift(
            #                y=windowed_grain_float,
            #                sr=sample_rate,
            #                n_steps=self._pitch_shift_semitones
            #            )
            #        if len(pitched_grain) > grain_length_samples:
            #            windowed_grain = pitched_grain[:grain_length_samples]
            #        elif len(pitched_grain) < grain_length_samples:
            #            windowed_grain = np.pad(pitched_grain, (0, grain_length_samples - len(pitched_grain)), mode='constant')
            #        else:
            #            windowed_grain = pitched_grain
            #    except Exception as e:
            #        print(f"Pitch shift error: {e}. Skipping pitch shift for this grain.")
            #        windowed_grain = grain_raw * hann(len(grain_raw))

            active_grains.append({
                'data': windowed_grain,
                'current_sample': 0,
                'total_samples': len(windowed_grain)
            })

        new_active_grains = []
        for grain in active_grains:
            grain_data = grain['data']
            current_sample_in_grain = grain['current_sample']
            total_samples_in_grain = grain['total_samples']

            remaining_in_grain = total_samples_in_grain - current_sample_in_grain
            samples_to_add = min(num_frames, remaining_in_grain)

            if samples_to_add > 0:
                grain_segment = grain_data[current_sample_in_grain: current_sample_in_grain + samples_to_add]

                if len(grain_segment) < samples_to_add:
                    grain_segment = np.pad(grain_segment, (0, samples_to_add - len(grain_segment)), mode='constant')
                elif len(grain_segment) > samples_to_add:
                    grain_segment = grain_segment[:samples_to_add]

                output_buffer[:samples_to_add] += grain_segment

                grain['current_sample'] += samples_to_add

            if grain['current_sample'] < total_samples_in_grain:
                new_active_grains.append(grain)

        # Write back updated grains and playhead in a short lock
        with self._lock:
            self._active_grains = new_active_grains
            self._current_loop_playhead_position = current_loop_playhead_position

        max_val = np.max(np.abs(output_buffer))
        if max_val > 1.0e-9:
            output_buffer /= max_val
        else:
            output_buffer = np.zeros_like(output_buffer)

        return output_buffer