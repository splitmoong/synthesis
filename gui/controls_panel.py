from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
import math


class Knob(QWidget):
    """
    A custom PyQt widget that mimics a rotary knob control.
    Emits valueChanged signal when rotated.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, min_val: int = 0, max_val: int = 100, initial_val: int = 0, label_text: str = "", parent=None):
        super().__init__(parent)
        self._min_val = min_val
        self._max_val = max_val
        self._value = initial_val
        self._range = max_val - min_val
        self._label_text = label_text

        self.setFixedSize(80, 100)  # Increased height to accommodate text
        self.setMouseTracking(True)
        self._dragging = False
        self._last_mouse_y = 0

    def value(self) -> int:
        return self._value

    def setValue(self, value: int):
        if self._min_val <= value <= self._max_val and self._value != value:
            self._value = value
            self.update()  # Redraw the knob
            self.valueChanged.emit(self._value)

    def setRange(self, min_val: int, max_val: int):
        self._min_val = min_val
        self._max_val = max_val
        self._range = max_val - min_val
        if not (self._min_val <= self._value <= self._max_val):
            self.setValue(self._min_val)
        self.update()

    def setLabelText(self, text: str):
        self._label_text = text
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_mouse_y = event.pos().y()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta_y = self._last_mouse_y - event.pos().y()
            # Adjust sensitivity as needed
            sensitivity = 0.5
            change = int(delta_y * sensitivity)

            new_value = self._value + change
            self.setValue(max(self._min_val, min(self._max_val, new_value)))
            self._last_mouse_y = event.pos().y()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect()
        knob_area_height = rect.height() * 0.7  # Allocate top 70% for knob, 30% for text
        knob_center_y = knob_area_height / 2

        center = self.rect().center()
        center.setY(int(knob_center_y))  # Adjust center for the knob drawing area

        # Ensure radius is an integer for drawEllipse with QPoint center
        radius = int(min(rect.width(), knob_area_height) / 2.5)

        # Draw knob background
        painter.setBrush(QColor("#3a3a3a"))
        painter.setPen(QColor("#555555"))
        painter.drawEllipse(center, radius, radius)

        # Draw indicator (line on the knob)
        indicator_radius = radius * 0.7
        angle_range = 270
        start_angle = 225

        normalized_value = (self._value - self._min_val) / self._range if self._range > 0 else 0
        current_angle = start_angle - (normalized_value * angle_range)

        angle_rad = math.radians(current_angle)

        indicator_x = center.x() + indicator_radius * math.cos(angle_rad)
        indicator_y = center.y() - indicator_radius * math.sin(angle_rad)

        painter.setPen(QPen(QColor("#00aaff"), 3))
        painter.drawLine(center.x(), center.y(), int(indicator_x), int(indicator_y))

        # Draw text below the knob
        text_rect = QRectF(0, knob_area_height, rect.width(), rect.height() - knob_area_height)
        painter.setPen(QColor("#e0e0e0"))
        painter.setFont(QFont("Arial", 10))  # Small font size
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._label_text)

        painter.end()


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
        self.grain_size_changed_signal.emit(self.grain_size_knob.value())
        self.grain_density_changed_signal.emit(self.grain_density_knob.value())
        self.pitch_shift_changed_signal.emit(self.pitch_shift_knob.value() / 10.0)
        self.volume_changed_signal.emit(self.volume_knob.value())

    def _init_ui(self):
        """
        Sets up the layout and initializes all control widgets.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Playback Controls Group ---
        playback_group = QGroupBox("Playback")
        playback_group.setFixedHeight(100)  # Ensure sufficient height
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
        playback_layout.addStretch(1)

        main_layout.addWidget(playback_group)

        # --- Granulation Parameters Group ---
        params_group = QGroupBox("Granulation Parameters")
        # Use QHBoxLayout for knobs to be side-by-side
        params_layout = QHBoxLayout(params_group)
        params_layout.setSpacing(15)  # Add some spacing between knobs

        # Helper function to create a knob with its value label below it
        def create_knob_column(label_text, min_val, max_val, initial_val):
            v_layout = QVBoxLayout()
            v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center content horizontally

            knob = Knob(min_val, max_val, initial_val, label_text)
            v_layout.addWidget(knob)

            value_label = QLabel(str(initial_val))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet("font-size: 12px; color: #b0b0b0;")  # Smaller and slightly dimmer
            v_layout.addWidget(value_label)

            return v_layout, knob, value_label

        # Grain Size Knob
        grain_size_v_layout, self.grain_size_knob, self.grain_size_value_label = \
            create_knob_column("Grain Size (ms)", 10, 500, 50)
        params_layout.addLayout(grain_size_v_layout)

        # Grain Density Knob
        grain_density_v_layout, self.grain_density_knob, self.grain_density_value_label = \
            create_knob_column("Grain Density (g/s)", 1, 100, 10)
        params_layout.addLayout(grain_density_v_layout)

        # Pitch Shift Knob
        pitch_shift_v_layout, self.pitch_shift_knob, self.pitch_shift_value_label = \
            create_knob_column("Pitch Shift (st)", -120, 120, 0)
        self.pitch_shift_value_label.setText(f"{self.pitch_shift_knob.value() / 10.0:.1f}")
        params_layout.addLayout(pitch_shift_v_layout)

        # Volume Knob
        volume_v_layout, self.volume_knob, self.volume_value_label = \
            create_knob_column("Volume (%)", 0, 100, 100)
        params_layout.addLayout(volume_v_layout)

        params_layout.addStretch(1)  # Push knobs to the left

        main_layout.addWidget(params_group)
        main_layout.addStretch(1)

        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #e0e0e0;
                padding-top: 20px;
                padding-bottom: 10px; /* Add some padding at the bottom for knobs */
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
            QPushButton {
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def _connect_signals(self):
        self.play_button.clicked.connect(self.play_signal.emit)
        self.stop_button.clicked.connect(self.stop_signal.emit)

        self.grain_size_knob.valueChanged.connect(self._update_grain_size)
        self.grain_density_knob.valueChanged.connect(self._update_grain_density)
        self.pitch_shift_knob.valueChanged.connect(self._update_pitch_shift)
        self.volume_knob.valueChanged.connect(self._update_volume)

    def _update_grain_size(self, value: int):
        self.grain_size_value_label.setText(str(value))
        self.grain_size_changed_signal.emit(value)

    def _update_grain_density(self, value: int):
        self.grain_density_value_label.setText(str(value))
        self.grain_density_changed_signal.emit(value)

    def _update_pitch_shift(self, value: int):
        float_value = value / 10.0
        self.pitch_shift_value_label.setText(f"{float_value:.1f}")
        self.pitch_shift_changed_signal.emit(float_value)

    def _update_volume(self, value: int):
        self.volume_value_label.setText(str(value))
        self.volume_changed_signal.emit(value)

    def on_playback_started(self):
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_playback_stopped(self):
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)