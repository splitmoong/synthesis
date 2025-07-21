# GranulatorApp/utils/constants.py

# Default audio sample rate in Hertz (Hz)
# Common values include 44100 Hz (CD quality) or 48000 Hz.
DEFAULT_SAMPLE_RATE = 44100

# Default length of a single grain in milliseconds (ms)
DEFAULT_GRAIN_LENGTH_MS = 50

# Default density of grains in grains per second (gps)
DEFAULT_GRAIN_DENSITY = 10

# Default size of audio buffers (frames) requested by PyAudio callback
# A common buffer size for real-time audio applications.
AUDIO_BUFFER_SIZE = 1024