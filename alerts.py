import time
class Notifier:
    def __init__(self, board, gpio_cfg):
        self.board = board
        self.on_ms = gpio_cfg["buzzer_on_ms"]
        self.off_ms = gpio_cfg["buzzer_off_ms"]
        self._last = 0.0
        self._beep_on = False

    def alert(self, active: bool):
        if not active:
            self.board.led_off(); self.board.buzz_off(); self._beep_on = False
            return
        self.board.led_on()
        now = time.time()*1000
        if not self._beep_on and now - self._last > self.off_ms:
            self.board.buzz_on(); self._beep_on = True; self._last = now
        elif self._beep_on and now - self._last > self.on_ms:
            self.board.buzz_off(); self._beep_on = False; self._last = now
