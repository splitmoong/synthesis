# GranulatorApp/gui/waveform_viewer.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal


class WaveformViewer(QWidget):
    """
    A PyQt widget that displays the waveform of an audio file using Matplotlib.
    """

    def __init__(self):
        """
        Initializes the WaveformViewer, setting up the Matplotlib figure
        and canvas.
        """
        super().__init__()
        self.audio_data = None
        self.sample_rate = None
        self.total_audio_duration_seconds = 0.0  # Store total duration

        # --- Granulation Visuals State ---
        self.start_pos_percentage = 0  # 0-100% of audio duration
        self.grain_size_percentage = 50  # NEW: Grain length as percentage (0-100)
        self.current_playback_pos_seconds = 0.0  # Current playback head position

        # Matplotlib plot elements for dynamic updates (store as instance variables)
        self.start_pos_line = None
        self.grain_region_patch = None
        self.playback_cursor_line = None

        self._init_ui()

    def _init_ui(self):
        """
        Sets up the layout and embeds the Matplotlib canvas.
        """
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 3), dpi=100, facecolor='#2a2a2a')
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2a2a2a')

        # Set initial plot properties (dark theme friendly)
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

    def update_waveform(self, audio_data: np.ndarray, sample_rate: int):
        """
        Updates the waveform display with new audio data.
        """
        self.audio_data = audio_data
        self.sample_rate = sample_rate

        self.ax.clear()  # Clear the previous plot elements (including old lines/patches)

        # Reset line/patch references so _draw_granulation_visuals creates them fresh
        self.start_pos_line = None
        self.grain_region_patch = None
        self.playback_cursor_line = None

        if self.audio_data is not None and self.sample_rate > 0 and len(self.audio_data) > 0:
            # NEW: Check for NaN/Inf in audio_data before plotting
            if np.isnan(self.audio_data).any() or np.isinf(self.audio_data).any():
                print("Warning: Waveform data contains NaN or Inf values. Not plotting waveform.")
                self.ax.set_title("Audio Data Error (NaN/Inf)", color='red')
                self.canvas.draw()
                self.total_audio_duration_seconds = 0.0  # Set to 0 if data is invalid
                return  # Exit if data is invalid

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

        else:
            self.ax.set_title("No Audio Loaded", color='#e0e0e0')
            self.total_audio_duration_seconds = 0.0

        # Reapply dark theme specific styles after clear()
        self.ax.set_facecolor('#2a2a2a')
        self.ax.tick_params(axis='x', colors='#e0e0e0')
        self.ax.tick_params(axis='y', colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#666')
        self.ax.spines['top'].set_color('#666')
        self.ax.spines['right'].set_color('#666')
        self.ax.spines['left'].set_color('#666')
        self.ax.grid(True, linestyle=':', alpha=0.6, color='#555')

        self._draw_granulation_visuals()  # Draw indicators for the (possibly new) audio
        self.figure.tight_layout()
        self.canvas.draw()

    # MODIFIED: grain_size_perc instead of grain_size_ms
    def update_granulation_visuals(self, start_pos_perc: int, grain_size_perc: int,
                                   current_playback_pos_seconds: float = 0.0):
        """
        Updates the parameters that define the visual indicators for granulation
        and redraws them.

        Args:
            start_pos_perc (int): Start position as a percentage (0-100).
            grain_size_perc (int): Grain size as a percentage (0-100) of total duration.
            current_playback_pos_seconds (float): Current playback time in seconds (for cursor).
        """
        self.start_pos_percentage = start_pos_perc
        self.grain_size_percentage = grain_size_perc  # Store as percentage
        self.current_playback_pos_seconds = current_playback_pos_seconds

        # Only redraw indicators if audio data is loaded and valid
        if self.audio_data is not None and self.sample_rate > 0 and self.total_audio_duration_seconds > 0:
            self._draw_granulation_visuals()
            self.canvas.draw_idle()  # Use draw_idle for more efficient updates (prevents flickering)
        else:
            # If no audio or invalid, hide any existing visuals
            if self.start_pos_line: self.start_pos_line.set_visible(False)
            if self.grain_region_patch: self.grain_region_patch.set_visible(False)
            if self.playback_cursor_line: self.playback_cursor_line.set_visible(False)
            self.canvas.draw_idle()

    def _draw_granulation_visuals(self):
        """
        Draws/updates the visual indicators for granulation (start line, grain region, cursor).
        This method is called by update_waveform and update_granulation_visuals.
        """
        if self.audio_data is None or self.total_audio_duration_seconds == 0:
            # Hide existing visuals if no audio is loaded
            if self.start_pos_line: self.start_pos_line.set_visible(False)
            if self.grain_region_patch: self.grain_region_patch.set_visible(False)
            if self.playback_cursor_line: self.playback_cursor_line.set_visible(False)
            return

        # --- Calculate positions based on percentages ---
        start_pos_seconds = self.total_audio_duration_seconds * (self.start_pos_percentage / 100.0)
        # Clamp start_pos_seconds to ensure it's within bounds
        start_pos_seconds = max(0.0, min(start_pos_seconds, self.total_audio_duration_seconds))

        # NEW: Calculate grain_length_seconds from percentage
        grain_length_seconds = self.total_audio_duration_seconds * (self.grain_size_percentage / 100.0)
        # Ensure grain_length_seconds is positive for meaningful display
        if grain_length_seconds <= 0.0:
            grain_length_seconds = 0.001  # Smallest visible length

        # --- Draw/Update Start Position Indicator ---
        if self.start_pos_line is None:
            self.start_pos_line = self.ax.axvline(
                x=start_pos_seconds, # This is fine for creation
                color='#FFA500',  # Orange
                linestyle='--',
                linewidth=2,
                label='Start Position'
            )
        else:
            # FIX: Pass a sequence (list) to set_xdata
            self.start_pos_line.set_xdata([start_pos_seconds]) # Pass as a list
            self.start_pos_line.set_visible(True)  # Ensure visible if it was hidden

        # --- Draw/Update Granulation Region (Shaded Rectangle) ---
        region_start_s = start_pos_seconds
        region_end_s = start_pos_seconds + grain_length_seconds

        # Ensure the region does not exceed audio boundaries (visual clamp)
        region_end_s = min(region_end_s, self.total_audio_duration_seconds)

        # Ensure region width is non-negative
        rect_width = max(0.0, region_end_s - region_start_s)

        if self.grain_region_patch is None:
            # Create a rectangle patch
            self.grain_region_patch = patches.Rectangle(
                (region_start_s, self.ax.get_ylim()[0]),  # (x, y) bottom-left corner
                rect_width,  # width
                self.ax.get_ylim()[1] - self.ax.get_ylim()[0],  # height (full axis height)
                facecolor='#00FFFF',  # Cyan
                alpha=0.2,  # Semi-transparent
                edgecolor='none',  # No border
                label='Granulation Region'
            )
            self.ax.add_patch(self.grain_region_patch)
        else:
            self.grain_region_patch.set_xy((region_start_s, self.ax.get_ylim()[0]))
            self.grain_region_patch.set_width(rect_width)
            self.grain_region_patch.set_height(
                self.ax.get_ylim()[1] - self.ax.get_ylim()[0])  # Update height in case y-limits changed
            self.grain_region_patch.set_visible(True)  # Ensure visible if it was hidden

        # --- Draw/Update Playback Cursor (Moving Vertical Line) ---
        # This line moves as the audio plays, showing the current read head within the loop.
        playback_cursor_s = 0.0  # Default if not valid

        if self.total_audio_duration_seconds > 0:  # Ensure audio loaded
            loop_start_s = start_pos_seconds
            loop_end_s = region_end_s  # This is the visual end of the loop

            loop_duration_s = max(0.001, loop_end_s - loop_start_s)  # Ensure positive loop duration

            # Calculate current_playback_pos_seconds relative to the loop start
            current_pos_relative_to_loop_start = self.current_playback_pos_seconds - loop_start_s

            # Use modulo to make the cursor loop within the loop_duration_s
            # For pure positive modulo behavior: (a % n + n) % n
            # Ensure the current_pos_relative_to_loop_start is non-negative for modulo logic
            if current_pos_relative_to_loop_start < 0:
                # If the playback position is before the loop start,
                # effectively treat it as if it's at loop_start_s for the modulo calculation,
                # or just snap to loop_start_s for the visual.
                # Let's snap to loop_start_s for simplicity, then the modulo will handle further movement
                cursor_pos_in_loop = 0.0
            else:
                cursor_pos_in_loop = np.fmod(current_pos_relative_to_loop_start, loop_duration_s)

            playback_cursor_s = loop_start_s + cursor_pos_in_loop

            # Ensure cursor stays within the visual bounds (loop_start_s to loop_end_s)
            playback_cursor_s = max(loop_start_s, min(playback_cursor_s, loop_end_s))

        # Check for valid cursor position (could be 0.0 if no audio or initial state)
        if playback_cursor_s >= 0 and playback_cursor_s <= self.total_audio_duration_seconds:
            if self.playback_cursor_line is None:
                self.playback_cursor_line = self.ax.axvline(
                    x=playback_cursor_s,
                    color='#FF0000',  # Red
                    linestyle='-',
                    linewidth=1.5,
                    label='Playback Cursor'
                )
            else:
                # FIX: Pass a sequence (list) to set_xdata
                self.playback_cursor_line.set_xdata([playback_cursor_s])
                self.playback_cursor_line.set_visible(True)  # Ensure visible
        else:
            # If cursor position is invalid (e.g., negative, or outside total duration), hide it
            if self.playback_cursor_line:
                self.playback_cursor_line.set_visible(False)