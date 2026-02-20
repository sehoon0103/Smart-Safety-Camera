from collections import deque
import numpy as np

class TemporalSmoother:
    def __init__(self, window=12, tflite_path=None):
        self.buf = deque(maxlen=window)
        self.lstm = None

        # 연속 프레임 기준 길이
        self.window = max(1, int(window))
        # unsafe 상태로 바뀌기 위한 최소 연속 프레임 수
        self.on_frames = max(1, self.window // 2)
        # safe 상태로 돌아가기 위한 최소 연속 프레임 수
        self.off_frames = max(1, self.window // 2)

        # 현재 최종 상태 (0.0: safe, 1.0: unsafe)
        self.state = 0.0
        self._run_unsafe = 0
        self._run_safe = 0


        if tflite_path:
            try:
                import tflite_runtime.interpreter as tflite
                self.lstm = tflite.Interpreter(model_path=tflite_path)
                self.lstm.allocate_tensors()
            except Exception:
                self.lstm = None

    def push(self, unsafe_prob: float):
        v = float(unsafe_prob)
        self.buf.append(v)

        # 0.5 기준으로 safe / unsafe 이진화 (rules.py에서 0/1로 들어오므로 사실상 그대로)
        if v >= 0.5:
            self._run_unsafe += 1
            self._run_safe = 0
        else:
            self._run_safe += 1
            self._run_unsafe = 0

        # 상태 전환 조건:
        # - on_frames 이상 연속 unsafe면 state = 1.0
        # - off_frames 이상 연속 safe면 state = 0.0
        if self._run_unsafe >= self.on_frames:
            self.state = 1.0
        elif self._run_safe >= self.off_frames:
            self.state = 0.0

    def decision(self) -> float:
        if not self.buf:
            return 0.0

        if self.lstm is None:
            return float(self.state)
        # TODO: tflite 입출력 텐서 연결(모델 사양 필요)
        return float(self.state)
