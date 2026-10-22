"""
main.py - run this file to start the Deadlock Simulator:

    python main.py
"""
import tkinter as tk

from gui import DeadlockApp


def main():
    # On Windows, ask for sharp (DPI-aware) rendering. Safe to ignore if it fails.
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    DeadlockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
