"""main.py - starts AirControl AI.   Run:  python main.py"""
from core.app_controller import AppController
from ui.main_window import MainWindow


def main():
    window = MainWindow(AppController())
    window.run()


if __name__ == "__main__":
    main()
