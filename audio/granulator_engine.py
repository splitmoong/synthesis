# GranulatorApp/audio/granulator_engine.py

import numpy as np
from scipy.signal.windows import hann # For applying a window to grains
import librosa.effects # For pitch shifting
import threading
import time # For potential timing in grain generation

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

        # Granulation parameters (initialized with defaults)
        self._grain_length_ms = DEFAULT_GRAIN_LENGTH_MS # milliseconds
        self._grain_density = DEFAULT_GRAIN_DENSITY     # grains per second
        self._pitch_shift_semitones = 0.0               # in semitones
        self._overlap_ratio = 0.5                       # overlap between grains (0.0 to 1.0)
        self._playhead_position = 0                     # Current position in the source audio (in samples)

        # List to hold currently active grains
        # Each grain will be a dictionary: {'data': np.ndarray, 'position': int, 'remaining_samples': int, 'current_sample': int}
        self._active_grains = []

        # Lock for thread-safe access to active_grains and playhead_position
        self._lock = threading.Lock()

        print(f"GranulatorEngine initialized. Default grain length: {self._grain_length_ms}ms, Density: {self._grain_density}gps")


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
            self._playhead_position = 0 # Reset playhead
            self._active_grains = []    # Clear active grains
            print(f"GranulatorEngine: Audio source updated. Length: {len(audio_data) / sample_rate:.2f}s, SR: {sample_rate}Hz")

    def set_grain_length_ms(self, length_ms: int):
        """Sets the grain length in milliseconds."""
        with self._lock:
            self._grain_length_ms = max(1, length_ms) # Ensure positive value
            print(f"GranulatorEngine: Grain length set to {self._grain_length_ms}ms")

    def set_grain_density(self, density: int):
        """Sets the grain density in grains per second."""
        with self._lock:
            self._grain_density = max(1, density) # Ensure positive value
            print(f"GranulatorEngine: Grain density set to {self._grain_density} grains/s")

    def set_pitch_shift(self, semitones: float):
        """Sets the pitch shift in semitones."""
        with self._lock:
            self._pitch_shift_semitones = semitones
            print(f"GranulatorEngine: Pitch shift set to {self._pitch_shift_semitones:.1f} semitones")

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
        if self._audio_data is None or self._sample_rate == 0:
            return np.zeros(num_frames, dtype=np.float32) # Return silence if no audio

        output_buffer = np.zeros(num_frames, dtype=np.float32)

        with self._lock:
            # Calculate grain parameters based on current settings
            grain_length_samples = int(self._sample_rate * (self._grain_length_ms / 1000.0))
            if grain_length_samples == 0: # Avoid division by zero or zero-length grains
                return output_buffer

            # Determine how often to trigger new grains based on density
            # This is a simplified approach; a more advanced granulator might use a probability
            # or a more complex timing mechanism.
            # We want to trigger 'self._grain_density' grains per second.
            # So, for 'num_frames' (which is a fraction of a second), we trigger:
            grains_to_trigger = int(self._grain_density * (num_frames / self._sample_rate))
            # Ensure at least one grain if density is high enough for the buffer size
            if self._grain_density > 0 and grains_to_trigger == 0 and num_frames > 0:
                 # If density is very low, trigger a grain every now and then
                 # This simple check ensures at least one grain is triggered if the buffer
                 # is large enough to contain a grain interval.
                 if (self._sample_rate / self._grain_density) <= num_frames:
                     grains_to_trigger = 1


            # --- 1. Advance Playhead and Trigger New Grains ---
            for _ in range(grains_to_trigger):
                # Choose a random start position within the source audio
                # For simplicity, let's pick a random point within the current view
                # or the entire audio if playhead is not strictly defined yet.
                if len(self._audio_data) > grain_length_samples:
                    # Random start point within the current audio data, avoiding end overflow
                    start_idx = np.random.randint(0, len(self._audio_data) - grain_length_samples)
                else:
                    start_idx = 0 # If audio is too short, just start at 0

                # Extract grain data
                grain_raw = self._audio_data[start_idx : start_idx + grain_length_samples]

                # Apply windowing function (e.g., Hanning window)
                window = hann(len(grain_raw))
                windowed_grain = grain_raw * window

                # Apply pitch shift if necessary
                if self._pitch_shift_semitones != 0.0:
                    # librosa.effects.pitch_shift can be computationally intensive for real-time
                    # For a simple approach, we apply it once per grain.
                    # For very low latency, pre-pitch-shifted versions or more optimized algorithms might be needed.
                    windowed_grain = librosa.effects.pitch_shift(
                        y=windowed_grain,
                        sr=self._sample_rate,
                        n_steps=self._pitch_shift_semitones
                    )
                    # Ensure the pitch-shifted grain has the correct length after resampling
                    # due to pitch shift. Pad or truncate if needed.
                    if len(windowed_grain) > grain_length_samples:
                        windowed_grain = windowed_grain[:grain_length_samples]
                    elif len(windowed_grain) < grain_length_samples:
                        windowed_grain = np.pad(windowed_grain, (0, grain_length_samples - len(windowed_grain)))


                # Add the new grain to the list of active grains
                self._active_grains.append({
                    'data': windowed_grain,
                    'current_sample': 0, # Current playback position within this grain
                    'total_samples': len(windowed_grain)
                })

            # --- 2. Process Active Grains and Mix into Output Buffer ---
            grains_to_remove = []
            for grain_idx, grain in enumerate(self._active_grains):
                grain_data = grain['data']
                current_sample_in_grain = grain['current_sample']
                total_samples_in_grain = grain['total_samples']

                # Determine how many samples of this grain can be added to the current buffer
                remaining_in_grain = total_samples_in_grain - current_sample_in_grain
                samples_to_add = min(num_frames, remaining_in_grain)

                if samples_to_add > 0:
                    # Extract the segment of the grain for this buffer
                    grain_segment = grain_data[current_sample_in_grain : current_sample_in_grain + samples_to_add]

                    # Mix the grain segment into the output buffer
                    # Ensure sizes match before adding
                    if len(grain_segment) == samples_to_add:
                        output_buffer[:samples_to_add] += grain_segment
                    else:
                        # This can happen if samples_to_add is larger than the actual grain_segment
                        # due to rounding or edge cases. Pad the segment to match.
                        padded_segment = np.pad(grain_segment, (0, samples_to_add - len(grain_segment)))
                        output_buffer[:samples_to_add] += padded_segment


                    # Update the grain's current playback position
                    grain['current_sample'] += samples_to_add

                # Mark grain for removal if it has finished playing
                if grain['current_sample'] >= total_samples_in_grain:
                    grains_to_remove.append(grain_idx)

            # Remove finished grains (iterate backwards to avoid index issues)
            for idx in sorted(grains_to_remove, reverse=True):
                del self._active_grains[idx]

            # Normalize output buffer to prevent clipping (simple gain reduction)
            # A more sophisticated approach would use dynamic range compression or limiter
            max_val = np.max(np.abs(output_buffer))
            if max_val > 1.0:
                output_buffer /= max_val

            return output_buffer

