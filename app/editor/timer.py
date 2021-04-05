import time

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, pyqtSignal

from app import constants
from app import counters

class Timer(QWidget):
    tick_elapsed = pyqtSignal()

    def __init__(self, fps=60):
        super().__init__()
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.tick)
        timer_speed = int(1000/float(fps))
        self.main_timer.setInterval(timer_speed)
        self.main_timer.start()

        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(5 * 60 * 1000)
        self.autosave_timer.start()

        framerate = 16
        self.passive_counter = counters.generic3counter(int(32*framerate), int(4*framerate))
        self.active_counter = counters.generic3counter(int(13*framerate), int(6*framerate))

    def tick(self):
        current_time = int(round(time.time() * 1000))
        self.passive_counter.update(current_time)
        self.active_counter.update(current_time)
        self.tick_elapsed.emit()

    def start(self):
        self.main_timer.start()
        self.autosave_timer.start()

    def start_for_editor(self):
        self.main_timer.start()

    def stop(self):
        self.main_timer.stop()
        self.autosave_timer.stop()

    def stop_for_editor(self):
        self.main_timer.stop()

TIMER = None
def get_timer():
    global TIMER
    if not TIMER:
        TIMER = Timer(constants.FPS//2)
    return TIMER
