from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

from gui.controls_panel import Knob


class EffectsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        reverb_group = QGroupBox("Reverb")
        reverb_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid gray;
                border-radius: 5px;
                margin-top: 20px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 14px;
            }
        """)

        reverb_layout = QVBoxLayout()
        self.reverb_toggle = QPushButton("Reverb On")
        self.reverb_toggle.setCheckable(True)
        self.reverb_toggle.setStyleSheet("padding: 6px;")
        reverb_layout.addWidget(self.reverb_toggle, alignment=Qt.AlignmentFlag.AlignCenter)

        knobs_layout = QHBoxLayout()

        # Reverb knobs (you can rename or adjust ranges)
        self.decay_knob = self.create_knob("Decay", 0.5)
        self.mix_knob = self.create_knob("Mix", 0.5)
        self.room_size_knob = self.create_knob("Room Size", 0.5)

        knobs_layout.addLayout(self.decay_knob)
        knobs_layout.addLayout(self.mix_knob)
        knobs_layout.addLayout(self.room_size_knob)

        reverb_layout.addLayout(knobs_layout)
        reverb_group.setLayout(reverb_layout)

        main_layout.addWidget(reverb_group)

    def create_knob(self, label, initial_value):
        layout = QVBoxLayout()
        knob = Knob(min_val=0, max_val=100, initial_val=int(initial_value * 100), label_text=label)
        knob.setFixedSize(64, 80)

        value_label = QLabel(f"{initial_value * 100:.0f}%")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("""
            font-size: 12px;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 4px;
            background-color: #222;
        """)

        layout.addWidget(knob, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        return layout
