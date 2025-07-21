# GranulatorApp/audio/audio_player.py

import pyaudio
import numpy as np
import threading
import time

from PyQt6.QtCore import pyqtSignal, QObject # QObject is needed for signals outside QWidgets

# Import constants for default values
from utils.constants import DEFAULT_SAMPLE_RATE, AUDIO_BUFFER_SIZE

class AudioPlayer(QObject): # Inherit from QObject to use pyqtSignal
    """
    Manages real-time audio playback using PyAudio.
    It runs in a separate thread and continuously requests audio buffers
    from the GranulatorEngine.
    """

    # Custom signals to inform the GUI about playback state
    playback_started_signal = pyqtSignal()
    playback_stopped_signal = pyqtSignal()

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
        self._playback_thread = None
        self._volume = 1.0 # Initial volume (0.0 to 1.0)

        print("AudioPlayer initialized.")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback function. This function is called by PyAudio
        whenever it needs more audio data.

        Args:
            in_data: Input audio data (not used for output stream).
            frame_count (int): The number of frames (samples) requested.
            time_info: Dictionary containing timing information.
            status: Bitfield of status flags.

        Returns:
            tuple: (output_buffer, pyaudio.paContinue or pyaudio.paComplete)
        """
        if self._is_playing:
            # Request a buffer from the granulator engine
            # The engine will generate granulated audio based on its parameters
            audio_buffer = self._granulator_engine.generate_audio_buffer(frame_count)

            # Apply volume
            audio_buffer = audio_buffer * self._volume

            # Convert to bytes for PyAudio. PyAudio expects float32 or int16/int32.
            # We'll use float32 as numpy arrays are typically float32.
            # Ensure the buffer is contiguous for PyAudio
            output_bytes = audio_buffer.astype(np.float32).tobytes()

            return output_bytes, pyaudio.paContinue
        else:
            # If not playing, return silence and indicate completion
            return np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paComplete

    def play(self):
        """
        Starts audio playback.
        """
        if self._is_playing:
            print("Audio already playing.")
            return

        print("Starting audio playback...")
        self._is_playing = True
        self.playback_started_signal.emit() # Emit signal to GUI

        # Start the PyAudio stream in a separate thread
        # It's crucial to open the stream in the same thread that will call the callback
        # or manage the stream. Here, the callback is managed by PyAudio's internal thread.
        # The .start_stream() call is non-blocking.
        try:
            self._stream = self._pyaudio.open(
                format=pyaudio.paFloat32, # We're using float32 numpy arrays
                channels=1,               # Mono audio
                rate=self._granulator_engine._sample_rate, # Use engine's sample rate
                output=True,              # Output stream
                frames_per_buffer=AUDIO_BUFFER_SIZE, # Number of frames per callback
                stream_callback=self._audio_callback # Our callback function
            )
            self._stream.start_stream()
            print("PyAudio stream started.")
        except Exception as e:
            print(f"Error starting PyAudio stream: {e}")
            self._is_playing = False
            self.playback_stopped_signal.emit() # Emit signal even on error
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
        self._is_playing = False
        self.playback_stopped_signal.emit() # Emit signal to GUI

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
                print("PyAudio stream stopped and closed.")
            except Exception as e:
                print(f"Error stopping/closing PyAudio stream: {e}")
            finally:
                self._stream = None # Ensure stream is None after closing

    def set_volume(self, volume_percent: int):
        """
        Sets the playback volume.

        Args:
            volume_percent (int): Volume as a percentage (0-100).
        """
        self._volume = np.clip(volume_percent / 100.0, 0.0, 1.0)
        print(f"AudioPlayer: Volume set to {volume_percent}%")

    def __del__(self):
        """
        Destructor to ensure PyAudio resources are properly released.
        """
        self.stop() # Ensure stream is stopped
        if self._pyaudio:
            self._pyaudio.terminate()
            print("PyAudio terminated.")

