# GranulatorApp/gui/waveform_viewer.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

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
        self._init_ui()

    def _init_ui(self):
        """
        Sets up the layout and embeds the Matplotlib canvas.
        """
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0) # No margins for the plot

        # Create a Matplotlib Figure and a FigureCanvas to display it
        self.figure = Figure(figsize=(5, 3), dpi=100, facecolor='#2a2a2a') # Dark background for the figure
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas)

        # Get the axes object from the figure
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2a2a2a') # Dark background for the axes

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

        # Set initial title (can be updated later)
        self.ax.set_title("No Audio Loaded", color='#e0e0e0')

        # Adjust layout to prevent labels from overlapping
        self.figure.tight_layout()

    def update_waveform(self, audio_data: np.ndarray, sample_rate: int):
        """
        Updates the waveform display with new audio data.

        Args:
            audio_data (np.ndarray): The audio time series (NumPy array).
            sample_rate (int): The sample rate of the audio.
        """
        self.audio_data = audio_data
        self.sample_rate = sample_rate

        self.ax.clear() # Clear the previous plot

        if self.audio_data is not None and self.sample_rate > 0:
            # Calculate time array for plotting
            time = np.linspace(0, len(self.audio_data) / self.sample_rate, num=len(self.audio_data))

            # Plot the waveform
            self.ax.plot(time, self.audio_data, color='#00aaff', linewidth=0.5) # Bright blue waveform

            self.ax.set_xlabel("Time (s)", color='#e0e0e0')
            self.ax.set_ylabel("Amplitude", color='#e0e0e0')
            self.ax.set_title("Audio Waveform", color='#e0e0e0')
            self.ax.set_xlim(0, time[-1] if time.size > 0 else 0) # Set x-axis limits
            self.ax.set_ylim(np.min(self.audio_data) * 1.1, np.max(self.audio_data) * 1.1) # Set y-axis limits with padding
        else:
            self.ax.set_title("No Audio Loaded", color='#e0e0e0') # Reset title if no data

        # Reapply grid and tick parameters after clearing
        self.ax.set_facecolor('#2a2a2a')
        self.ax.tick_params(axis='x', colors='#e0e0e0')
        self.ax.tick_params(axis='y', colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#666')
        self.ax.spines['top'].set_color('#666')
        self.ax.spines['right'].set_color('#666')
        self.ax.spines['left'].set_color('#666')
        self.ax.grid(True, linestyle=':', alpha=0.6, color='#555')

        self.figure.tight_layout() # Adjust layout again
        self.canvas.draw() # Redraw the canvas to show the updated plot