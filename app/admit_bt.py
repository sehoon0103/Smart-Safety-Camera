import bluetooth
import threading

class AdminNotifier:
    """
    라즈베리파이를 블루투스 RFCOMM 서버로 올려두고,
    관리자가 스마트폰(App Inventor)으로 접속하면
    send.state()로 문자열을 보내는 간단한 알림용 클래스.
    """
    def __init__(self):
        self.sock = None
        self.last_state = None  # "SAFE" / "NO_HELMET"
        t = threading.Thread(target=self._wait_for_connection, daemon=True)
        t.start()
        print("[BT]백그라운드에서 관리자연결대기중")



    def _wait_for_connection(self):
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", 1))   # 채널 1 (SPP 기본)
        server_sock.listen(1)
        print("[BT] 관리자의 폰 연결을 기다리는 중... (App Inventor에서 연결 버튼 누르기)")

        client_sock, addr = server_sock.accept()
        print(f"[BT] 관리자 폰 연결됨: {addr}")
        self.sock = client_sock
        server_sock.close()

    def send_state(self, unsafe: bool):
        """
        unsafe == True  → "NO_HELMET"
        unsafe == False → "SAFE"
        같은 상태가 연속으로 나오면 중복 전송 안 함.
        """
        if self.sock is None:
            return

        state = "NO_HELMET" if unsafe else "SAFE"
        if state == self.last_state:
            return  # 상태가 안 바뀌었으면 굳이 또 안 보냄

        try:
            msg = state + "\n"
            self.sock.send(msg.encode("utf-8"))
            print(f"[BT] 관리자에게 전송: {state}")
            self.last_state = state
        except OSError as e:
            print(f"[BT] 전송 실패, 재연결 필요할 수 있음: {e}")
            # 필요하면 여기서 다시 _wait_for_connection() 호출해서 재연결 로직 넣어도 됨.
