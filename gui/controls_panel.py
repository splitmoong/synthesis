# GranulatorApp/gui/controls_panel.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class ControlsPanel(QWidget):
    """
    A PyQt widget that provides controls for granulator parameters
    and audio playback (play/stop).
    """

    # Define custom signals to be emitted when controls are changed
    play_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    grain_size_changed_signal = pyqtSignal(int)  # Emits grain size in ms
    grain_density_changed_signal = pyqtSignal(int)  # Emits grain density (e.g., grains per second)
    pitch_shift_changed_signal = pyqtSignal(float)  # Emits pitch shift in semitones
    volume_changed_signal = pyqtSignal(int)  # Emits volume percentage (0-100)

    def __init__(self):
        """
        Initializes the ControlsPanel, setting up the UI elements.
        """
        super().__init__()
        self._init_ui()
        self._connect_signals()

        # Set initial values for controls
        self.grain_size_changed_signal.emit(self.grain_size_slider.value())
        self.grain_density_changed_signal.emit(self.grain_density_slider.value())
        self.pitch_shift_changed_signal.emit(self.pitch_shift_slider.value() / 10.0)  # Convert to float semitones
        self.volume_changed_signal.emit(self.volume_slider.value())

    def _init_ui(self):
        """
        Sets up the layout and initializes all control widgets.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Playback Controls Group ---
        playback_group = QGroupBox("Playback")
        playback_layout = QHBoxLayout(playback_group)
        playback_layout.setSpacing(10)

        self.play_button = QPushButton("Play")
        self.play_button.setFixedSize(100, 40)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Green */
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #388E3C;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #367c39;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
                border: 1px solid #555;
            }
        """)
        playback_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedSize(100, 40)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336; /* Red */
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #d32f2f;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
                border: 1px solid #555;
            }
        """)
        playback_layout.addWidget(self.stop_button)
        playback_layout.addStretch(1)  # Push buttons to the left

        main_layout.addWidget(playback_group)

        # --- Granulation Parameters Group ---
        params_group = QGroupBox("Granulation Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(10)

        # Grain Size Slider
        grain_size_layout = QHBoxLayout()
        grain_size_layout.addWidget(QLabel("Grain Size (ms):"))
        self.grain_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.grain_size_slider.setRange(10, 500)  # 10 ms to 500 ms
        self.grain_size_slider.setValue(50)  # Default value
        self.grain_size_slider.setSingleStep(5)
        self.grain_size_slider.setPageStep(20)
        self.grain_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.grain_size_slider.setTickInterval(50)
        grain_size_layout.addWidget(self.grain_size_slider)
        self.grain_size_value_label = QLabel(str(self.grain_size_slider.value()))
        self.grain_size_value_label.setFixedWidth(40)
        grain_size_layout.addWidget(self.grain_size_value_label)
        params_layout.addLayout(grain_size_layout)

        # Grain Density Slider
        grain_density_layout = QHBoxLayout()
        grain_density_layout.addWidget(QLabel("Grain Density (grains/s):"))
        self.grain_density_slider = QSlider(Qt.Orientation.Horizontal)
        self.grain_density_slider.setRange(1, 100)  # 1 grain/s to 100 grains/s
        self.grain_density_slider.setValue(10)  # Default value
        self.grain_density_slider.setSingleStep(1)
        self.grain_density_slider.setPageStep(10)
        self.grain_density_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.grain_density_slider.setTickInterval(10)
        grain_density_layout.addWidget(self.grain_density_slider)
        self.grain_density_value_label = QLabel(str(self.grain_density_slider.value()))
        self.grain_density_value_label.setFixedWidth(40)
        grain_density_layout.addWidget(self.grain_density_value_label)
        params_layout.addLayout(grain_density_layout)

        # Pitch Shift Slider
        pitch_shift_layout = QHBoxLayout()
        pitch_shift_layout.addWidget(QLabel("Pitch Shift (semitones):"))
        self.pitch_shift_slider = QSlider(Qt.Orientation.Horizontal)
        # Range from -120 to +120 (representing -12.0 to +12.0 semitones)
        self.pitch_shift_slider.setRange(-120, 120)
        self.pitch_shift_slider.setValue(0)  # Default: no pitch shift
        self.pitch_shift_slider.setSingleStep(1)  # 0.1 semitone steps
        self.pitch_shift_slider.setPageStep(10)  # 1 semitone steps
        self.pitch_shift_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.pitch_shift_slider.setTickInterval(20)  # Every 2 semitones
        pitch_shift_layout.addWidget(self.pitch_shift_slider)
        self.pitch_shift_value_label = QLabel(f"{self.pitch_shift_slider.value() / 10.0:.1f}")
        self.pitch_shift_value_label.setFixedWidth(40)
        pitch_shift_layout.addWidget(self.pitch_shift_value_label)
        params_layout.addLayout(pitch_shift_layout)

        # Volume Slider
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume (%):"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)  # 0% to 100%
        self.volume_slider.setValue(100)  # Default: 100%
        self.volume_slider.setSingleStep(1)
        self.volume_slider.setPageStep(10)
        self.volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.volume_slider.setTickInterval(10)
        volume_layout.addWidget(self.volume_slider)
        self.volume_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_value_label.setFixedWidth(40)
        volume_layout.addWidget(self.volume_value_label)
        params_layout.addLayout(volume_layout)

        main_layout.addWidget(params_group)

        # Add a stretch to push everything to the top
        main_layout.addStretch(1)

        # Apply dark theme styling to controls
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                background-color: #282828;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: #333;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00aaff; /* Bright blue handle */
                border: 1px solid #0088cc;
                width: 18px;
                margin: -5px 0; /* handle is 16px wide, so -2 to center it */
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #0088cc; /* Darker blue for filled part */
                border: 1px solid #006699;
                height: 8px;
                border-radius: 4px;
            }
            QSpinBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def _connect_signals(self):
        """
        Connects UI element signals to internal slots and emits custom signals.
        """
        self.play_button.clicked.connect(self.play_signal.emit)
        self.stop_button.clicked.connect(self.stop_signal.emit)

        self.grain_size_slider.valueChanged.connect(self._update_grain_size)
        self.grain_density_slider.valueChanged.connect(self._update_grain_density)
        self.pitch_shift_slider.valueChanged.connect(self._update_pitch_shift)
        self.volume_slider.valueChanged.connect(self._update_volume)

    def _update_grain_size(self, value: int):
        """Updates the grain size label and emits the signal."""
        self.grain_size_value_label.setText(str(value))
        self.grain_size_changed_signal.emit(value)

    def _update_grain_density(self, value: int):
        """Updates the grain density label and emits the signal."""
        self.grain_density_value_label.setText(str(value))
        self.grain_density_changed_signal.emit(value)

    def _update_pitch_shift(self, value: int):
        """Updates the pitch shift label and emits the signal (converting to float)."""
        float_value = value / 10.0
        self.pitch_shift_value_label.setText(f"{float_value:.1f}")
        self.pitch_shift_changed_signal.emit(float_value)

    def _update_volume(self, value: int):
        """Updates the volume label and emits the signal."""
        self.volume_value_label.setText(str(value))
        self.volume_changed_signal.emit(value)

    def on_playback_started(self):
        """Slot to disable play button and enable stop button when playback starts."""
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_playback_stopped(self):
        """Slot to enable play button and disable stop button when playback stops."""
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
