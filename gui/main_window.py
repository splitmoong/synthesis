import os

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox,
    QLabel, QStackedWidget  # NEW: Import QStackedWidget for overlay
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QShortcut

# Import components from other modules
from gui.waveform_viewer import WaveformViewer
from gui.controls_panel import ControlsPanel
from gui.effects_panel import EffectsPanel
from audio.audio_loader import AudioLoader
from audio.granulator_engine import GranulatorEngine
from audio.audio_player import AudioPlayer
from utils.constants import DEFAULT_SAMPLE_RATE


class MainWindow(QMainWindow):
    """
    The main application window for the Granulator App.
    Handles overall layout, file drag-and-drop, and coordination
    between GUI and audio processing components.
    """

    audio_loaded_signal = pyqtSignal(object, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Synthesis")
        self.setGeometry(100, 100, 600, 400)

        self.setAcceptDrops(True)

        self.audio_data = None
        self.sample_rate = DEFAULT_SAMPLE_RATE

        self.granulator_engine = GranulatorEngine(None, self.sample_rate)
        self.audio_player = AudioPlayer(self.granulator_engine)

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(100)  # Increased interval for better responsiveness
        self.playback_timer.timeout.connect(self._update_playback_cursor)

        self.shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut.activated.connect(self._toggle_playback_with_spacebar)

        self._init_ui()
        self._connect_signals()

        # Initial visualization update (for empty state or default loaded audio)
        # This is called once on startup to set the initial state of visuals.
        self.waveform_viewer.update_granulation_visuals(
            self.controls_panel.start_position_knob.value(),
            self.controls_panel.grain_size_knob.value(),
            0.0
        )

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Waveform Viewer and Drag & Drop Overlay
        # Use a QStackedWidget to layer the WaveformViewer and the drag/drop label
        self.waveform_stack = QStackedWidget()
        self.waveform_viewer = WaveformViewer()
        self.waveform_viewer.setMinimumHeight(250)
        # Removed the border style line as requested
        # self.waveform_viewer.setStyleSheet("border: 1px solid #444; border-radius: 8px; background-color: #2a2a2a;")

        # Add WaveformViewer as the first (bottom) widget
        self.waveform_stack.addWidget(self.waveform_viewer)

        # Create the drag and drop label and add it as the second (top) widget
        self.drag_drop_label = QLabel("Drag & Drop an Audio File (WAV, MP3) Here")
        self.drag_drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_drop_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #888;
                padding: 10px;
                border: 2px dashed #666;
                border-radius: 10px;
                margin: 20px;
                background-color: rgba(42, 42, 42, 0.8); /* Semi-transparent overlay */
            }
        """)
        self.waveform_stack.addWidget(self.drag_drop_label)

        # Initially show the drag_drop_label (index 1)
        self.waveform_stack.setCurrentIndex(1)

        main_layout.addWidget(self.waveform_stack, 3)  # Give it vertical stretch

        # 2. Controls Panel
        self.controls_panel = ControlsPanel()
        self.controls_panel.setStyleSheet("border: 1px solid #444; border-radius: 8px; background-color: #333;")
        self.controls_panel.setContentsMargins(0, 0, 0, 0)
        controls_wrapper = QWidget()
        controls_layout = QVBoxLayout(controls_wrapper)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)
        controls_layout.addWidget(self.controls_panel)
        main_layout.addWidget(controls_wrapper, 1)

        #self.effects_panel = EffectsPanel()
        #self.effects_panel.setStyleSheet("border: 1px solid #444; border-radius: 8px; background-color: #333;")
        #main_layout.addWidget(self.effects_panel, 1)

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
        self.audio_loaded_signal.connect(self.waveform_viewer.update_waveform)

        self.controls_panel.play_signal.connect(self._start_playback_and_timer)
        self.controls_panel.stop_signal.connect(self._stop_playback_and_timer)
        self.controls_panel.grain_size_changed_signal.connect(self.granulator_engine.set_grain_length_percentage)
        self.controls_panel.grain_density_changed_signal.connect(self.granulator_engine.set_grain_density)
        self.controls_panel.pitch_shift_changed_signal.connect(self.granulator_engine.set_pitch_shift)
        self.controls_panel.volume_changed_signal.connect(self.audio_player.set_volume)
        self.controls_panel.start_position_changed_signal.connect(self.granulator_engine.set_start_position_percentage)

        self.audio_player.playback_started_signal.connect(self.controls_panel.on_playback_started)
        self.audio_player.playback_stopped_signal.connect(self.controls_panel.on_playback_stopped)

        self.controls_panel.grain_size_changed_signal.connect(
            lambda size: self.waveform_viewer.update_granulation_visuals(
                self.controls_panel.start_position_knob.value(),
                size,
                self.audio_player.get_current_playback_time()
            )
        )
        self.controls_panel.start_position_changed_signal.connect(
            lambda pos: self.waveform_viewer.update_granulation_visuals(
                pos,
                self.controls_panel.grain_size_knob.value(),
                self.audio_player.get_current_playback_time()
            )
        )
        self.audio_player.playback_progress_signal.connect(
            lambda current_time: self.waveform_viewer.update_granulation_visuals(
                self.controls_panel.start_position_knob.value(),
                self.controls_panel.grain_size_knob.value(),
                current_time
            )
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    if filepath.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    self._load_and_display_audio(filepath)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _load_and_display_audio(self, filepath: str):
        # Hide the drag and drop overlay by showing the waveform viewer
        self.waveform_stack.setCurrentIndex(0)  # Show WaveformViewer (index 0)

        audio_data, sample_rate = AudioLoader.load_audio(filepath)

        if audio_data is not None and sample_rate is not None:
            self.audio_data = audio_data
            self.sample_rate = sample_rate

            self.audio_loaded_signal.emit(self.audio_data, self.sample_rate)
            self.granulator_engine.set_audio_source(self.audio_data, self.sample_rate)
            self.audio_player.reset_playback()

            self.waveform_viewer.update_granulation_visuals(
                self.controls_panel.start_position_knob.value(),
                self.controls_panel.grain_size_knob.value(),
                0.0
            )

            QMessageBox.information(self, "Audio Loaded", f"Successfully loaded: {os.path.basename(filepath)}")
        else:
            QMessageBox.warning(self, "Loading Error", f"Could not load audio file: {os.path.basename(filepath)}")
            # If loading fails, show the drag and drop overlay again
            self.waveform_stack.setCurrentIndex(1)  # Show Drag & Drop Label (index 1)

    def _start_playback_and_timer(self):
        if self.audio_data is None:
            QMessageBox.warning(self, "No Audio", "Please load an audio file first.")
            return

        # Ensure audio player has the latest granulator engine parameters
        # This is important if parameters were tweaked while stopped
        self.granulator_engine.set_start_position_percentage(self.controls_panel.start_position_knob.value())
        self.granulator_engine.set_grain_length_percentage(self.controls_panel.grain_size_knob.value())
        self.granulator_engine.set_grain_density(self.controls_panel.grain_density_knob.value())
        self.granulator_engine.set_pitch_shift(
            self.controls_panel.pitch_shift_knob.value() / 10.0)  # Convert to float semitones

        self.audio_player.play()
        self.playback_timer.start()

    def _stop_playback_and_timer(self):
        self.audio_player.stop()
        self.playback_timer.stop()
        self.waveform_viewer.update_granulation_visuals(
            self.controls_panel.start_position_knob.value(),
            self.controls_panel.grain_size_knob.value(),
            self.audio_player.get_current_playback_time()
        )

    def _update_playback_cursor(self):
        current_time = self.audio_player.get_current_playback_time()
        self.waveform_viewer.update_granulation_visuals(
            self.controls_panel.start_position_knob.value(),
            self.controls_panel.grain_size_knob.value(),
            current_time
        )

    def _toggle_playback_with_spacebar(self):
        # Check audio_player's internal _is_playing state
        if self.audio_player._is_playing:  # Access internal flag
            self._stop_playback_and_timer()
        else:
            self._start_playback_and_timer()