# In GranulatorApp/main.py

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

import cProfile
import pstats
import signal  # NEW: Import signal module


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# NEW: Signal handler to dump profile on Ctrl+C
def signal_handler(sig, frame):
    print("\nCtrl+C detected. Dumping profile stats...")
    if profiler:  # Ensure profiler exists and is enabled
        try:
            profiler.disable()
            stats_file = "granulator_profile_stats_interrupt.prof"
            profiler.dump_stats(stats_file)
            print(f"Profiling results saved to {stats_file}")

            print("\n--- Top 20 functions by cumulative time (on interrupt) ---")
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumtime')
            stats.print_stats(20)

        except Exception as e:
            print(f"Error dumping profile on interrupt: {e}")
    sys.exit(0)  # Exit the application


if __name__ == "__main__":
    profiler = cProfile.Profile()

    # NEW: Register the signal handler BEFORE enabling the profiler and running app
    signal.signal(signal.SIGINT, signal_handler)  # SIGINT is for Ctrl+C

    profiler.enable()

    try:
        main()
    finally:
        # This block will still execute if main() finishes normally
        # or if an unhandled exception occurs *before* a SIGINT.
        # It's good practice to keep it for normal exits.
        if profiler:  # Check if profiler is still active
            try:
                profiler.disable()
                stats_file = "granulator_profile_stats_normal_exit.prof"
                profiler.dump_stats(stats_file)
                print(f"\nProfiling results saved to {stats_file}")

                print("\n--- Top 20 functions by cumulative time ---")
                stats = pstats.Stats(profiler)
                stats.sort_stats('cumtime')
                stats.print_stats(20)

                print("\n--- Top 20 functions by total time (excluding subcalls) ---")
                stats.sort_stats('tottime')
                stats.print_stats(20)
            except Exception as e:
                print(f"Error dumping profile on normal exit: {e}")