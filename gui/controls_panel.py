# In GranulatorApp/gui/controls_panel.py

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
        self._label_text = label_text # Keep label_text for internal knowledge, but not for drawing here

        # Adjusted height: Now set to a size that's good for JUST the knob,
        # as text will be handled by QLabels in the parent layout.
        self.setFixedSize(80, 80) # Optimal size for the knob itself
        self.setMouseTracking(True)
        self._dragging = False
        self._last_mouse_y = 0

    def value(self) -> int:
        return self._value

    def setValue(self, value: int):
        if self._min_val <= value <= self._max_val and self._value != value:
            self._value = value
            self.update()
            self.valueChanged.emit(self._value)

    def setRange(self, min_val: int, max_val: int):
        self._min_val = min_val
        self._max_val = max_val
        self._range = max_val - min_val
        if not (self._min_val <= self._value <= self._max_val):
            self.setValue(self._min_val)
        self.update()

    def setLabelText(self, text: str):
        # This method is less relevant now as label text is shown via a separate QLabel
        self._label_text = text
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_mouse_y = event.pos().y()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta_y = self._last_mouse_y - event.pos().y()
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

        rect = self.rect()
        knob_radius = min(rect.width(), rect.height()) / 2.5
        knob_center = rect.center()

        painter.setBrush(QColor("#3a3a3a"))
        painter.setPen(QColor("#555555"))
        # FIX: Cast knob_radius to int for drawEllipse
        painter.drawEllipse(knob_center, int(knob_radius), int(knob_radius))

        indicator_radius = knob_radius * 0.7
        angle_range = 270
        start_angle = 225

        normalized_value = (self._value - self._min_val) / self._range if self._range > 0 else 0
        current_angle = start_angle - (normalized_value * angle_range)

        angle_rad = math.radians(current_angle)

        indicator_x = knob_center.x() + indicator_radius * math.cos(angle_rad)
        indicator_y = knob_center.y() - indicator_radius * math.sin(angle_rad)

        painter.setPen(QPen(QColor("#00aaff"), 3))
        painter.drawLine(knob_center.x(), knob_center.y(), int(indicator_x), int(indicator_y))

        painter.end()


class ControlsPanel(QWidget):
    """
    A PyQt widget that provides controls for granulator parameters
    and audio playback (play/stop).
    """

    play_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    grain_size_changed_signal = pyqtSignal(int)
    grain_density_changed_signal = pyqtSignal(int)
    pitch_shift_changed_signal = pyqtSignal(float)
    volume_changed_signal = pyqtSignal(int)
    start_position_changed_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._connect_signals()

        self.grain_size_changed_signal.emit(self.grain_size_knob.value())
        self.grain_density_changed_signal.emit(self.grain_density_knob.value())
        self.pitch_shift_changed_signal.emit(self.pitch_shift_knob.value() / 10.0)
        self.volume_changed_signal.emit(self.volume_knob.value())
        self.start_position_changed_signal.emit(self.start_position_knob.value())

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        params_group = QGroupBox("")
        params_vertical_layout = QVBoxLayout(params_group)
        params_vertical_layout.setSpacing(15)  # Increased spacing within the group

        knobs_and_buttons_h_layout = QHBoxLayout()
        knobs_and_buttons_h_layout.setContentsMargins(0, 0, 0, 0)
        knobs_and_buttons_h_layout.setSpacing(10)
        self.knobs_layout = knobs_and_buttons_h_layout

        def create_knob_column(label_text, min_val, max_val, initial_val):
            v_layout = QVBoxLayout()
            v_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)  # Align top

            knob = Knob(min_val, max_val, initial_val, label_text, parent=self)
            knob_container = QHBoxLayout()
            knob_container.addStretch()
            knob_container.addWidget(knob)
            knob_container.addStretch()
            v_layout.addLayout(knob_container)

            value_label = QLabel(str(initial_val))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet("font-size: 12px; color: #b0b0b0;")
            v_layout.addWidget(value_label)

            text_label = QLabel(label_text)
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_label.setStyleSheet("font-size: 12px; color: #d0d0d0;")
            text_label.setFixedWidth(110)  # Set a fixed width to prevent wrapping
            text_label.setWordWrap(False)  # Ensure no wrapping
            v_layout.addWidget(text_label)

            # Reduced spacing between knob and value label
            v_layout.setSpacing(2)

            return v_layout, knob, value_label

        start_position_v_layout, self.start_position_knob, self.start_position_value_label = \
            create_knob_column("Start Pos (%)", 0, 100, 0)
        knobs_and_buttons_h_layout.addLayout(start_position_v_layout)

        grain_size_v_layout, self.grain_size_knob, self.grain_size_value_label = \
            create_knob_column("Grain Size (%)", 1, 100, 50)
        knobs_and_buttons_h_layout.addLayout(grain_size_v_layout)

        grain_density_v_layout, self.grain_density_knob, self.grain_density_value_label = \
            create_knob_column("Grain Density (g/s)", 1, 100, 2)
        knobs_and_buttons_h_layout.addLayout(grain_density_v_layout)

        pitch_shift_v_layout, self.pitch_shift_knob, self.pitch_shift_value_label = \
            create_knob_column("Pitch Shift (st)", -120, 120, 0)
        self.pitch_shift_value_label.setText(f"{self.pitch_shift_knob.value() / 10.0:.1f}")
        knobs_and_buttons_h_layout.addLayout(pitch_shift_v_layout)

        volume_v_layout, self.volume_knob, self.volume_value_label = \
            create_knob_column("Volume (%)", 0, 100, 100)
        knobs_and_buttons_h_layout.addLayout(volume_v_layout)

        knobs_and_buttons_h_layout.addStretch(1)

        self.play_button = QPushButton("Play")
        self.play_button.setFixedSize(80, 35)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
        """)
        knobs_and_buttons_h_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedSize(80, 35)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
        """)
        knobs_and_buttons_h_layout.addWidget(self.stop_button)

        params_vertical_layout.addLayout(knobs_and_buttons_h_layout)

        main_layout.addWidget(params_group)

        main_layout.addStretch(1)

        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 8px;
                font-weight: bold;
                color: #e0e0e0;
                padding-top: 40px;
                padding-bottom: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                background-color: #282828;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                /* FIX: Increase padding-top here for more space below the title */
                padding-top: 10px; /* You can adjust this value (e.g., 20px, 30px) */
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
        self.start_position_knob.valueChanged.connect(self._update_start_position)

    def _update_grain_size(self, value: int):
        self.grain_size_value_label.setText(f"{value}%")
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

    def _update_start_position(self, value: int):
        self.start_position_value_label.setText(f"{value}%")
        self.start_position_changed_signal.emit(value)

    def on_playback_started(self):
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_playback_stopped(self):
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)