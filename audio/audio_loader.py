# GranulatorApp/audio/audio_loader.py

import librosa
import numpy as np
import os

class AudioLoader:
    """
    A static class responsible for loading audio files into a NumPy array
    and returning the audio data along with its sample rate.
    """

    @staticmethod
    def load_audio(filepath: str) -> tuple[np.ndarray | None, int | None]:
        """
        Loads an audio file from the given filepath using librosa.

        Args:
            filepath (str): The full path to the audio file (e.g., .wav, .mp3).

        Returns:
            tuple[np.ndarray | None, int | None]: A tuple containing:
                - audio_data (np.ndarray): The audio time series as a NumPy array,
                                          or None if loading fails.
                - sample_rate (int): The sample rate of the audio, or None if
                                     loading fails.
        """
        if not os.path.exists(filepath):
            print(f"Error: File not found at '{filepath}'")
            return None, None

        try:
            # librosa.load can handle various formats (WAV, MP3, FLAC, OGG, etc.)
            # It automatically resamples to 22050 Hz by default.
            # Set sr=None to load at the original sample rate.
            y, sr = librosa.load(filepath, sr=None)
            print(f"Successfully loaded '{os.path.basename(filepath)}' with sample rate: {sr} Hz")
            return y, sr
        except Exception as e:
            # Catch any exceptions during loading (e.g., unsupported format, corrupted file)
            print(f"Error loading audio file '{os.path.basename(filepath)}': {e}")
            return None, None

