from picamera2 import Picamera2
import time

class Camera:
    def __init__(self, cam_cfg):
        self.picam2 = Picamera2()
        cfg = self.picam2.create_preview_configuration(
            main={"size": (cam_cfg["width"], cam_cfg["height"]), "format": "RGB888"},
            buffer_count=4
        )
        self.picam2.configure(cfg); self.picam2.start(); time.sleep(0.3)
    def read(self):
        import cv2
        frm = self.picam2.capture_array()
        return cv2.cvtColor(frm, cv2.COLOR_RGB2BGR)
    def close(self):
        self.picam2.stop()

class GPIOBoard:
    def __init__(self, gpio_cfg):
        from gpiozero import LED, Buzzer
        self.led = LED(gpio_cfg["led_pin"])
        self.buzzer = Buzzer(gpio_cfg["buzzer_pin"])

    def led_on(self): self.led.on()
    def led_off(self): self.led.off()
    def buzz_on(self): self.buzzer.on()
    def buzz_off(self): self.buzzer.off()
