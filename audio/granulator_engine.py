# GranulatorApp/audio/granulator_engine.py

import numpy as np
from scipy.signal.windows import hann  # For applying a window to grains
import librosa.effects  # For pitch shifting
import threading
import time  # For potential timing in grain generation

# Import constants for default values
from utils.constants import DEFAULT_GRAIN_LENGTH_MS, DEFAULT_GRAIN_DENSITY, DEFAULT_SAMPLE_RATE, AUDIO_BUFFER_SIZE


class GranulatorEngine:
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
        # NEW: Store total audio samples for percentage calculations
        self._total_audio_samples = 0
        if audio_data is not None:
            self._total_audio_samples = len(audio_data)

        # Granulation parameters (initialized with defaults)
        self._grain_length_percentage = 50  # NEW: Now percentage (0-100)
        self._grain_density = DEFAULT_GRAIN_DENSITY  # grains per second
        self._pitch_shift_semitones = 0.0  # in semitones
        self._overlap_ratio = 0.5  # overlap between grains (0.0 to 1.0)

        # Conceptual playhead position for the granulation engine.
        # This will now represent the position *within the active loop/region*, not global audio.
        self._current_loop_playhead_position = 0

        self._start_position_percentage = 0  # Start position from 0-100%
        self._start_position_sample = 0  # Calculated start position in samples

        # List to hold currently active grains
        # Each grain will be a dictionary: {'data': np.ndarray, 'current_sample': int, 'total_samples': int}
        self._active_grains = []

        # Lock for thread-safe access to active_grains and playhead_position
        self._lock = threading.Lock()

        print(
            f"GranulatorEngine initialized. Default grain length: {self._grain_length_percentage}%, Density: {self._grain_density}gps")

    def set_audio_source(self, audio_data: np.ndarray, sample_rate: int):
        """
        Sets or updates the source audio for the granulator.
        Resets the playhead and clears active grains.

        Args:
            audio_data (np.ndarray): The new audio time series.
            sample_rate (int): The sample rate of the new audio.
        """
        with self._lock:
            self._audio_data = audio_data
            self._sample_rate = sample_rate
            self._total_audio_samples = len(audio_data) if audio_data is not None else 0

            self._active_grains = []  # Clear active grains
            self._calculate_start_position_sample()  # Re-calculate _start_position_sample when audio source changes

            # NEW: Reset loop playhead when new audio is loaded
            self._current_loop_playhead_position = 0

            if self._audio_data is not None:
                print(
                    f"GranulatorEngine: Audio source updated. Length: {self._total_audio_samples / sample_rate:.2f}s, SR: {sample_rate}Hz")
            else:
                print("GranulatorEngine: Audio source cleared.")

    # MODIFIED: Grain length based on percentage
    def set_grain_length_percentage(self, percentage: int):
        """Sets the grain length as a percentage of the total audio length."""
        with self._lock:
            self._grain_length_percentage = max(1, min(100, percentage))  # Store percentage
            print(f"GranulatorEngine: Grain length set to {self._grain_length_percentage}%")

    def set_grain_density(self, density: int):
        """Sets the grain density in grains per second."""
        with self._lock:
            self._grain_density = max(1, density)  # Ensure positive value
            print(f"GranulatorEngine: Grain density set to {self._grain_density} grains/s")

    def set_pitch_shift(self, semitones: float):
        """Sets the pitch shift in semitones."""
        with self._lock:
            self._pitch_shift_semitones = semitones
            print(f"GranulatorEngine: Pitch shift set to {self._pitch_shift_semitones:.1f} semitones")

    def set_start_position_percentage(self, percentage: int):
        """
        Sets the start position for granulation as a percentage of the audio length.
        This defines the base point from which grains are typically drawn.

        Args:
            percentage (int): The start position percentage (0-100).
        """
        with self._lock:
            self._start_position_percentage = max(0, min(100, percentage))
            self._calculate_start_position_sample()  # Recalculate sample position
            # NEW: Reset loop playhead to the new start position when base start position changes
            self._current_loop_playhead_position = 0
            print(f"GranulatorEngine: Start Position set to {self._start_position_percentage}%")

    def _calculate_start_position_sample(self):
        """
        Calculates the start position in samples based on the percentage
        and the current audio data length.
        """
        if self._audio_data is not None and self._total_audio_samples > 0:
            self._start_position_sample = int(self._total_audio_samples * (self._start_position_percentage / 100.0))
            # Ensure it doesn't exceed bounds, or at least leaves space for a minimal grain
            self._start_position_sample = min(self._start_position_sample, self._total_audio_samples - 1)
            self._start_position_sample = max(0, self._start_position_sample)
        else:
            self._start_position_sample = 0

    # NEW METHOD: To provide the active loop region to AudioPlayer/WaveformViewer
    def get_current_loop_region(self) -> tuple[int, int]:
        """
        Returns the current start and end of the conceptual granulation loop region in SAMPLES.
        This is used for waveform visualization and AudioPlayer's cursor looping.
        """
        if self._audio_data is None or self._sample_rate <= 0 or self._total_audio_samples == 0:
            return 0, 0

        with self._lock:
            loop_start_sample = self._start_position_sample

            # Calculate loop_length_samples based on percentage
            loop_length_samples = int(self._total_audio_samples * (self._grain_length_percentage / 100.0))
            # Ensure a minimum positive length
            if loop_length_samples <= 0: loop_length_samples = 1

            loop_end_sample = min(loop_start_sample + loop_length_samples, self._total_audio_samples)

            # If the calculated loop end wraps around the actual audio end,
            # this gets tricky for a simple start/end point.
            # For visualization, we will show the segment from start_position to (start_position + grain_length).
            # The red bar will loop within this, so loop_end_sample is the end for the cursor.

            return loop_start_sample, loop_end_sample

    import numpy as np
    from scipy.signal.windows import hann  # For applying a window to grains
    import librosa.effects  # For pitch shifting (if you uncomment it later)
    import threading
    import time  # For potential timing in grain generation

    # Import constants for default values
    from utils.constants import DEFAULT_GRAIN_LENGTH_MS, DEFAULT_GRAIN_DENSITY, DEFAULT_SAMPLE_RATE, AUDIO_BUFFER_SIZE

    class GranulatorEngine:
        # ... (existing __init__ and other methods like set_audio_source, set_grain_length_percentage, etc.) ...

        def generate_audio_buffer(self, num_frames: int) -> np.ndarray:
            """
            Generates a buffer of granulated audio. This method is called repeatedly
            by the AudioPlayer to get audio data.

            Args:
                num_frames (int): The number of audio frames (samples) to generate.

            Returns:
                np.ndarray: A NumPy array containing the generated audio buffer.
                            Returns a zero array if no audio source is loaded.
            """
            # Ensure audio data and sample rate are valid before proceeding
            if self._audio_data is None or self._sample_rate <= 0 or self._total_audio_samples == 0:
                return np.zeros(num_frames, dtype=np.float32)

            output_buffer = np.zeros(num_frames, dtype=np.float32)

            with self._lock:
                audio_length = self._total_audio_samples  # Use the stored total samples

                # Calculate grain_length_samples based on percentage
                grain_length_samples = int(audio_length * (self._grain_length_percentage / 100.0))
                if grain_length_samples <= 0:
                    grain_length_samples = 1  # Ensure minimum 1 sample grain length for processing

                # Calculate the effective loop range in samples from get_current_loop_region
                loop_start_sample_actual, loop_end_sample_actual = self.get_current_loop_region()
                loop_duration_samples = loop_end_sample_actual - loop_start_sample_actual
                if loop_duration_samples <= 0: loop_duration_samples = 1  # Ensure non-zero loop duration for calculations

                # Determine how often to trigger new grains based on density
                if self._grain_density <= 0:
                    grains_to_trigger = 0
                else:
                    grains_to_trigger = int(self._grain_density * (num_frames / self._sample_rate))
                    if grains_to_trigger == 0 and (self._sample_rate / self._grain_density) <= num_frames:
                        grains_to_trigger = 1  # Ensure at least one grain if density allows

                # --- 1. Advance Internal Loop Playhead and Trigger New Grains ---
                # Advance the playhead that determines where new grains are spawned from *within the loop*.
                self._current_loop_playhead_position = (self._current_loop_playhead_position + num_frames)

                # Loop the _current_loop_playhead_position within the defined loop duration
                if loop_duration_samples > 0:
                    self._current_loop_playhead_position %= loop_duration_samples
                else:
                    self._current_loop_playhead_position = 0

                for _ in range(grains_to_trigger):
                    # Calculate base start of the grain within the entire audio
                    # Grains will spawn relative to the 'loop_start_sample_actual' and advance by `_current_loop_playhead_position`
                    grain_base_start_idx_in_loop = self._current_loop_playhead_position

                    # Add a small random deviation to grain start for textural variety
                    # Deviation should be relative to the grain length, and clamped to avoid extreme values.
                    deviation_range_samples = int(grain_length_samples * 0.5)  # Max +/- 50% of grain length
                    # Ensure deviation range is not negative
                    deviation_range_samples = max(0, deviation_range_samples)

                    if deviation_range_samples == 0:
                        random_deviation = 0
                    else:
                        random_deviation = np.random.randint(-deviation_range_samples, deviation_range_samples + 1)

                    # Final source index for this specific grain in the original audio data
                    # This index is relative to the start of the entire _audio_data array
                    grain_source_start_idx = loop_start_sample_actual + grain_base_start_idx_in_loop + random_deviation

                    # --- Robust Grain Extraction with numpy.take for Wrap-Around ---
                    # np.take with mode='wrap' handles indices outside [0, audio_length) by wrapping.
                    # This simplifies the complex if/else logic for concatenation.

                    # Create an array of indices for the grain
                    # Ensure indices are integers
                    indices = np.arange(grain_source_start_idx, grain_source_start_idx + grain_length_samples,
                                        dtype=int)

                    # Use numpy.take to get the grain data, which handles wrapping around the source array
                    grain_raw = np.take(self._audio_data, indices, mode='wrap')

                    # Apply windowing function (e.g., Hanning window)
                    # Ensure window has correct length, especially if grain_raw length somehow differs
                    window = hann(len(grain_raw))
                    windowed_grain = grain_raw * window

                    # Apply pitch shift if necessary
                    # Re-add pitch shift if you want, but keep in mind its performance impact.
                    # The robust checks for size and sample_rate are already good.
                    # if self._pitch_shift_semitones != 0.0:
                    #    # ... (your pitch shift code) ...
                    #    pass # placeholder for commented-out pitch shift

                    # Add the new grain to the list of active grains
                    self._active_grains.append({
                        'data': windowed_grain,
                        'current_sample': 0,
                        'total_samples': len(windowed_grain)
                    })

                # --- 2. Process Active Grains and Mix into Output Buffer ---
                # Optimize grain removal using list comprehension for efficiency
                # This avoids repeated 'del' calls which can be slow for large lists.
                new_active_grains = []
                for grain in self._active_grains:
                    grain_data = grain['data']
                    current_sample_in_grain = grain['current_sample']
                    total_samples_in_grain = grain['total_samples']

                    remaining_in_grain = total_samples_in_grain - current_sample_in_grain
                    samples_to_add = min(num_frames, remaining_in_grain)

                    if samples_to_add > 0:
                        grain_segment = grain_data[current_sample_in_grain: current_sample_in_grain + samples_to_add]

                        # Ensure grain_segment has the correct length for mixing
                        if len(grain_segment) < samples_to_add:
                            grain_segment = np.pad(grain_segment, (0, samples_to_add - len(grain_segment)),
                                                   mode='constant')
                        elif len(grain_segment) > samples_to_add:
                            grain_segment = grain_segment[:samples_to_add]

                        output_buffer[:samples_to_add] += grain_segment

                        grain['current_sample'] += samples_to_add

                    # Keep grain if it's not finished
                    if grain['current_sample'] < total_samples_in_grain:
                        new_active_grains.append(grain)

                self._active_grains = new_active_grains  # Update the list of active grains

                # Normalize output buffer to prevent clipping (simple gain reduction)
                # Add a small epsilon to prevent division by zero if max_val is 0 (all silence)
                max_val = np.max(np.abs(output_buffer))
                if max_val > 1.0e-9:  # Use a small threshold instead of exact zero
                    output_buffer /= max_val
                else:
                    output_buffer = np.zeros_like(output_buffer)  # If effectively silent, ensure it's all zeros

                return output_buffer