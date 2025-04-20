# osc_sender.py
from pythonosc import udp_client

class OSCSender:
    def __init__(self, host: str, port: int):
        self.client = udp_client.SimpleUDPClient(host, port)

    def send(self, path: str, value):
        # VRChat expects ints/floats/bools
        self.client.send_message(path, value)
