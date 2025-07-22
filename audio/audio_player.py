# GranulatorApp/audio/audio_player.py

import pyaudio
import numpy as np
import threading
import time

from PyQt6.QtCore import pyqtSignal, QObject

# Import constants for default values
from utils.constants import DEFAULT_SAMPLE_RATE, AUDIO_BUFFER_SIZE


class AudioPlayer(QObject):
    """
    Manages real-time audio playback using PyAudio.
    It runs in a separate thread and continuously requests audio buffers
    from the GranulatorEngine.
    """

    # Custom signals to inform the GUI about playback state
    playback_started_signal = pyqtSignal()
    playback_stopped_signal = pyqtSignal()
    # NEW: Signal to emit current playback time for waveform visualization
    playback_progress_signal = pyqtSignal(float)  # Emits current time in seconds

    def __init__(self, granulator_engine):
        """
        Initializes the AudioPlayer.

        Args:
            granulator_engine: An instance of GranulatorEngine to get audio buffers from.
        """
        super().__init__()
        self._granulator_engine = granulator_engine
        self._pyaudio = pyaudio.PyAudio()
        self._stream = None
        self._is_playing = False
        self._volume = 1.0  # Initial volume (0.0 to 1.0)

        # NEW: Playback position tracker (in frames)
        self._playback_position_frames = 0
        # NEW: Lock for thread-safe access to _playback_position_frames
        self._pos_lock = threading.Lock()

        print("AudioPlayer initialized.")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback function. This function is called by PyAudio
        whenever it needs more audio data.
        """
        if self._is_playing:
            audio_buffer = self._granulator_engine.generate_audio_buffer(frame_count)
            audio_buffer = audio_buffer * self._volume
            output_bytes = audio_buffer.astype(np.float32).tobytes()

            # NEW: Update playback position
            with self._pos_lock:
                self._playback_position_frames += frame_count
                # Optionally, loop the playback position if it exceeds total audio length
                # This depends on how your granulator handles looping.
                # If granulator loops automatically, the player's cursor might also loop.
                if self._granulator_engine._audio_data is not None and self._granulator_engine._sample_rate > 0:
                    total_samples = len(self._granulator_engine._audio_data)
                    if total_samples > 0:
                        self._playback_position_frames %= total_samples  # Loop the cursor

            # NEW: Emit playback progress signal
            # This is critical for updating the waveform viewer's cursor
            current_time_seconds = self.get_current_playback_time()
            self.playback_progress_signal.emit(current_time_seconds)

            return output_bytes, pyaudio.paContinue
        else:
            return np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paComplete

    def play(self):
        """
        Starts audio playback.
        """
        if self._is_playing:
            print("Audio already playing.")
            return

        if self._granulator_engine._audio_data is None:
            print("Cannot play: No audio data loaded in granulator engine.")
            return

        print("Starting audio playback...")
        self._is_playing = True
        self.playback_started_signal.emit()

        try:
            self._stream = self._pyaudio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self._granulator_engine._sample_rate,
                output=True,
                frames_per_buffer=AUDIO_BUFFER_SIZE,
                stream_callback=self._audio_callback
            )
            self._stream.start_stream()
            print("PyAudio stream started.")
        except Exception as e:
            print(f"Error starting PyAudio stream: {e}")
            self._is_playing = False
            self.playback_stopped_signal.emit()
            if self._stream:
                self._stream.close()
                self._stream = None

    def stop(self):
        """
        Stops audio playback.
        """
        if not self._is_playing:
            print("Audio not playing.")
            return

        print("Stopping audio playback...")
        self._is_playing = False  # Set flag immediately to stop callback
        self.playback_stopped_signal.emit()

        if self._stream:
            try:
                # Give a small moment for the callback to acknowledge _is_playing change
                # (though usually not strictly necessary with PyAudio's internal threading)
                time.sleep(0.01)
                if self._stream.is_active():  # Only stop if still active
                    self._stream.stop_stream()
                self._stream.close()
                print("PyAudio stream stopped and closed.")
            except Exception as e:
                print(f"Error stopping/closing PyAudio stream: {e}")
            finally:
                self._stream = None

    def set_volume(self, volume_percent: int):
        """
        Sets the playback volume.
        """
        self._volume = np.clip(volume_percent / 100.0, 0.0, 1.0)
        print(f"AudioPlayer: Volume set to {volume_percent}%")

    def get_current_playback_time(self) -> float:
        """
        Returns the current playback position in seconds.
        """
        with self._pos_lock:
            if self._granulator_engine._sample_rate > 0:
                return self._playback_position_frames / self._granulator_engine._sample_rate
            return 0.0

    def reset_playback(self):
        """
        Resets the internal playback position of the audio player to the beginning.
        Also stops playback if currently active.
        """
        if self._is_playing:
            self.stop()  # Stop playback first

        with self._pos_lock:
            self._playback_position_frames = 0  # Reset player's cursor
        # If your GranulatorEngine has its own internal playback head for
        # source audio advancement that needs to be reset on a player stop/reset,
        # you'd reset it here as well.
        # self._granulator_engine._playhead_position = 0 # Example: if granulator uses this

        print("AudioPlayer: Playback position reset.")

    def __del__(self):
        """
        Destructor to ensure PyAudio resources are properly released.
        """
        self.stop()  # Ensure stream is stopped
        if self._pyaudio:
            self._pyaudio.terminate()
            print("PyAudio terminated.")