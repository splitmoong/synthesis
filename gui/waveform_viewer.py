# GranulatorApp/gui/waveform_viewer.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QFont  # NEW: Import QPainter and QFont for custom paintEvent


class WaveformViewer(QWidget):
    """
    A PyQt widget that displays the waveform of an audio file using Matplotlib.
    """

    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.sample_rate = None
        self.total_audio_duration_seconds = 0.0

        # Overlay text for drag & drop or no audio loaded
        self.overlay_text = "Drag & Drop an Audio File (WAV, MP3) Here"
        self.show_overlay = True  # Initial state is to show overlay

        # --- Granulation Visuals State ---
        self.start_pos_percentage = 0
        self.grain_size_percentage = 50
        self.current_playback_pos_seconds = 0.0

        # Matplotlib plot elements for dynamic updates (initialized to None)
        self.start_pos_line = None
        self.grain_region_patch = None
        self.playback_cursor_line = None

        self._init_ui()  # This will now also call _draw_granulation_visuals

    def _init_ui(self):
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 3), dpi=100, facecolor='#2a2a2a')
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2a2a2a')

        self.ax.set_xlabel("Time (s)", color='#e0e0e0')
        self.ax.set_ylabel("Amplitude", color='#e0e0e0')
        self.ax.tick_params(axis='x', colors='#e0e0e0')
        self.ax.tick_params(axis='y', colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#666')
        self.ax.spines['top'].set_color('#666')
        self.ax.spines['right'].set_color('#666')
        self.ax.spines['left'].set_color('#666')
        self.ax.grid(True, linestyle=':', alpha=0.6, color='#555')

        self.ax.set_title("No Audio Loaded", color='#e0e0e0')
        self.figure.tight_layout()

        # Call _draw_granulation_visuals here to create the initial plot elements
        # They will be hidden if no audio is loaded, but their objects will exist.
        self._draw_granulation_visuals()
        self.canvas.draw()  # Draw the initial empty plot with hidden elements

    def set_overlay_text(self, text: str):
        """
        Sets the text to display as an overlay and controls its visibility.
        An empty string will hide the overlay.
        """
        self.overlay_text = text
        self.show_overlay = bool(text)  # True if text is non-empty, False otherwise
        self.update()  # Request a repaint to show/hide the overlay

    def update_waveform(self, audio_data: np.ndarray, sample_rate: int):
        self.audio_data = audio_data
        self.sample_rate = sample_rate

        self.ax.clear()

        # Crucially, after ax.clear(), we must reset the references so _draw_granulation_visuals recreates them.
        self.start_pos_line = None
        self.grain_region_patch = None
        self.playback_cursor_line = None

        if self.audio_data is not None and self.sample_rate > 0 and len(self.audio_data) > 0:
            if np.isnan(self.audio_data).any() or np.isinf(self.audio_data).any():
                print("Warning: Waveform data contains NaN or Inf values. Not plotting waveform.")
                self.ax.set_title("Audio Data Error (NaN/Inf)", color='red')
                self.canvas.draw()
                self.total_audio_duration_seconds = 0.0
                return

            self.total_audio_duration_seconds = len(self.audio_data) / self.sample_rate
            time = np.linspace(0, self.total_audio_duration_seconds, num=len(self.audio_data))

            self.ax.plot(time, self.audio_data, color='#00aaff', linewidth=0.5)

            self.ax.set_xlabel("Time (s)", color='#e0e0e0')
            self.ax.set_ylabel("Amplitude", color='#e0e0e0')
            self.ax.set_title("Audio Waveform", color='#e0e0e0')
            self.ax.set_xlim(0, self.total_audio_duration_seconds)
            y_min = np.min(self.audio_data)
            y_max = np.max(self.audio_data)
            padding = (y_max - y_min) * 0.1
            self.ax.set_ylim(y_min - padding, y_max + padding)

            # Hide overlay text when audio is loaded successfully
            self.set_overlay_text("")

        else:
            self.ax.set_title("No Audio Loaded", color='#e0e0e0')
            self.total_audio_duration_seconds = 0.0
            # Show overlay text if audio loading fails or no audio
            self.set_overlay_text("Drag & Drop an Audio File (WAV, MP3) Here")

        self.ax.set_facecolor('#2a2a2a')
        self.ax.tick_params(axis='x', colors='#e0e0e0')
        self.ax.tick_params(axis='y', colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#666')
        self.ax.spines['top'].set_color('#666')
        self.ax.spines['right'].set_color('#666')
        self.ax.spines['left'].set_color('#666')
        self.ax.grid(True, linestyle=':', alpha=0.6, color='#555')

        self._draw_granulation_visuals()
        self.figure.tight_layout()
        self.canvas.draw()

    def update_granulation_visuals(self, start_pos_perc: int, grain_size_perc: int,
                                   current_playback_pos_seconds: float = 0.0):
        self.start_pos_percentage = start_pos_perc
        self.grain_size_percentage = grain_size_perc
        self.current_playback_pos_seconds = current_playback_pos_seconds

        if self.audio_data is not None and self.sample_rate > 0 and self.total_audio_duration_seconds > 0:
            self._draw_granulation_visuals()
            self.canvas.draw_idle()
        else:
            # If no audio or invalid, hide any existing visuals
            if self.start_pos_line: self.start_pos_line.set_visible(False)
            if self.grain_region_patch: self.grain_region_patch.set_visible(False)
            if self.playback_cursor_line: self.playback_cursor_line.set_visible(False)
            self.canvas.draw_idle()

    def _draw_granulation_visuals(self):
        if self.audio_data is None or self.total_audio_duration_seconds == 0:
            # Hide visuals if no audio is loaded.
            if self.start_pos_line: self.start_pos_line.set_visible(False)
            if self.grain_region_patch: self.grain_region_patch.set_visible(False)
            if self.playback_cursor_line: self.playback_cursor_line.set_visible(False)
            return

        start_pos_seconds = self.total_audio_duration_seconds * (self.start_pos_percentage / 100.0)
        start_pos_seconds = max(0.0, min(start_pos_seconds, self.total_audio_duration_seconds))

        grain_length_seconds = self.total_audio_duration_seconds * (self.grain_size_percentage / 100.0)
        if grain_length_seconds <= 0.0:
            grain_length_seconds = 0.001

        # --- Draw/Update Start Position Indicator ---
        if self.start_pos_line is None:
            self.start_pos_line = self.ax.axvline(
                x=start_pos_seconds,
                color='#FFA500',
                linestyle='--',
                linewidth=2,
                label='Start Position'
            )
        else:
            self.start_pos_line.set_xdata([start_pos_seconds])
            self.start_pos_line.set_visible(True)

        # --- Draw/Update Granulation Region (Shaded Rectangle) ---
        region_start_s = start_pos_seconds
        region_end_s = start_pos_seconds + grain_length_seconds

        region_end_s = min(region_end_s, self.total_audio_duration_seconds)
        rect_width = max(0.0, region_end_s - region_start_s)

        if self.grain_region_patch is None:
            self.grain_region_patch = patches.Rectangle(
                (region_start_s, self.ax.get_ylim()[0]),
                rect_width,
                self.ax.get_ylim()[1] - self.ax.get_ylim()[0],
                facecolor='#00FFFF',
                alpha=0.2,
                edgecolor='none',
                label='Granulation Region'
            )
            self.ax.add_patch(self.grain_region_patch)
        else:
            self.grain_region_patch.set_xy((region_start_s, self.ax.get_ylim()[0]))
            self.grain_region_patch.set_width(rect_width)
            self.grain_region_patch.set_height(
                self.ax.get_ylim()[1] - self.ax.get_ylim()[0])
            self.grain_region_patch.set_visible(True)

        # --- Draw/Update Playback Cursor (Moving Vertical Line) ---
        playback_cursor_s = 0.0

        if self.total_audio_duration_seconds > 0:
            loop_start_s = start_pos_seconds
            loop_end_s = region_end_s

            loop_duration_s = max(0.001, loop_end_s - loop_start_s)

            current_pos_relative_to_loop_start = self.current_playback_pos_seconds - loop_start_s

            if current_pos_relative_to_loop_start < 0:
                playback_cursor_s = loop_start_s
            else:
                cursor_pos_in_loop = np.fmod(current_pos_relative_to_loop_start, loop_duration_s)
                playback_cursor_s = loop_start_s + cursor_pos_in_loop

            playback_cursor_s = max(loop_start_s, min(playback_cursor_s, loop_end_s))

        if playback_cursor_s >= 0 and playback_cursor_s <= self.total_audio_duration_seconds:
            if self.playback_cursor_line is None:
                self.playback_cursor_line = self.ax.axvline(
                    x=playback_cursor_s,
                    color='#FF0000',
                    linestyle='-',
                    linewidth=1.5,
                    label='Playback Cursor'
                )
            else:
                self.playback_cursor_line.set_xdata([playback_cursor_s])
                self.playback_cursor_line.set_visible(True)
        else:
            if self.playback_cursor_line:
                self.playback_cursor_line.set_visible(False)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.show_overlay and self.overlay_text:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.GlobalColor.gray)
            font = painter.font()
            font.setPointSize(16)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.overlay_text)