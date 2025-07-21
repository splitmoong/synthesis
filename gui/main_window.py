import os

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox,
    QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal # Import pyqtSignal for custom signals
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

# Import components from other modules
from gui.waveform_viewer import WaveformViewer
from gui.controls_panel import ControlsPanel
from audio.audio_loader import AudioLoader
from audio.granulator_engine import GranulatorEngine
from audio.audio_player import AudioPlayer
from utils.constants import DEFAULT_SAMPLE_RATE # Import default sample rate

class MainWindow(QMainWindow):
    """
    The main application window for the Granulator App.
    Handles overall layout, file drag-and-drop, and coordination
    between GUI and audio processing components.
    """

    # Custom signal to emit when a new audio file is loaded
    audio_loaded_signal = pyqtSignal(object, int) # Emits (audio_data, sample_rate)

    def __init__(self):
        """
        Initializes the MainWindow, sets up the UI, and connects components.
        """
        super().__init__()
        self.setWindowTitle("Granulator App")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        self.setAcceptDrops(True) # Enable drag and drop for the window

        self.audio_data = None
        self.sample_rate = DEFAULT_SAMPLE_RATE # Initialize with a default sample rate

        # Initialize audio components (these will be managed by MainWindow)
        self.granulator_engine = GranulatorEngine(self.audio_data, self.sample_rate)
        self.audio_player = AudioPlayer(self.granulator_engine)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """
        Sets up the main user interface layout.
        """
        # Central widget to hold the main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout for the entire window
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # Add some padding
        main_layout.setSpacing(15) # Spacing between widgets

        # 1. Waveform Viewer
        self.waveform_viewer = WaveformViewer()
        self.waveform_viewer.setMinimumHeight(250) # Ensure it has enough space
        self.waveform_viewer.setStyleSheet("border: 1px solid #444; border-radius: 8px; background-color: #2a2a2a;")
        main_layout.addWidget(self.waveform_viewer, 3) # Give it more vertical stretch

        # Add a placeholder label for drag and drop instructions
        self.drag_drop_label = QLabel("Drag & Drop an Audio File (WAV, MP3) Here")
        self.drag_drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_drop_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #888;
                padding: 50px;
                border: 2px dashed #666;
                border-radius: 10px;
                margin: 20px;
            }
        """)
        main_layout.addWidget(self.drag_drop_label)


        # 2. Controls Panel
        self.controls_panel = ControlsPanel()
        self.controls_panel.setStyleSheet("border: 1px solid #444; border-radius: 8px; background-color: #333;")
        main_layout.addWidget(self.controls_panel, 1) # Give it less vertical stretch

        # Set a dark theme for the window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QWidget {
                background-color: #282828;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)

    def _connect_signals(self):
        """
        Connects signals from UI elements to appropriate slots.
        """
        # Connect the custom audio_loaded_signal to the waveform viewer
        self.audio_loaded_signal.connect(self.waveform_viewer.update_waveform)

        # Connect controls panel signals to granulator engine and audio player
        self.controls_panel.play_signal.connect(self.audio_player.play)
        self.controls_panel.stop_signal.connect(self.audio_player.stop)
        self.controls_panel.grain_size_changed_signal.connect(self.granulator_engine.set_grain_length_ms)
        self.controls_panel.grain_density_changed_signal.connect(self.granulator_engine.set_grain_density)
        self.controls_panel.pitch_shift_changed_signal.connect(self.granulator_engine.set_pitch_shift)
        self.controls_panel.volume_changed_signal.connect(self.audio_player.set_volume)

        # Connect audio player state signals back to controls panel (e.g., to enable/disable buttons)
        self.audio_player.playback_started_signal.connect(self.controls_panel.on_playback_started)
        self.audio_player.playback_stopped_signal.connect(self.controls_panel.on_playback_stopped)


    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Handles drag-enter events to determine if the dragged data can be accepted.
        """
        if event.mimeData().hasUrls():
            # Check if any of the URLs are audio files
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    # Basic check for common audio extensions
                    if filepath.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        Handles drop events, loading the dropped audio file.
        """
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    self._load_and_display_audio(filepath)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _load_and_display_audio(self, filepath: str):
        """
        Loads an audio file, updates the waveform viewer, and sets the
        audio data for the granulator engine.
        """
        self.drag_drop_label.hide() # Hide the drag and drop label once a file is loaded

        # Load audio using the AudioLoader
        audio_data, sample_rate = AudioLoader.load_audio(filepath)

        if audio_data is not None and sample_rate is not None:
            self.audio_data = audio_data
            self.sample_rate = sample_rate

            # Emit signal to update waveform viewer
            self.audio_loaded_signal.emit(self.audio_data, self.sample_rate)

            # Update the granulator engine with the new audio source
            self.granulator_engine.set_audio_source(self.audio_data, self.sample_rate)

            QMessageBox.information(self, "Audio Loaded", f"Successfully loaded: {os.path.basename(filepath)}")
        else:
            QMessageBox.warning(self, "Loading Error", f"Could not load audio file: {os.path.basename(filepath)}")
            # If loading fails, show the drag and drop label again
            self.drag_drop_label.show()

