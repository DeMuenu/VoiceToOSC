# voice.py
import threading
import queue
import json
import sys
import os
import gc
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class VoiceRecognizer:
    def __init__(self, callback, partial_callback, model_path="models/vosk-model-small-en-us-0.15", device=None):
        """
        callback(phrase: str)
        """
        if not os.path.isdir(str(model_path)):
            print(
                f"Vosk model directory not found at '{model_path}'. "
                "Please download models from: https://alphacephei.com/vosk/models and extract to models/...  Defaulting to models/vosk-model-small-en-us-0.15"
            )
            model_path = "models/vosk-model-small-en-us-0.15"
        print(model_path)


        self.callback = callback
        self.partial_callback = partial_callback
        self.q = queue.Queue()
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self._stop_event = threading.Event()
        self.device = device

    def _audio_callback(self, indata, frames, time, status):
        if status:
            # Print any audio stream warnings to stderr
            print(f"Audio status: {status}", file=sys.stderr)
        self.q.put(bytes(indata))

    def _listen_loop(self):
        print("VoiceRecognizer started listening")  # notify start
        with sd.RawInputStream(
            samplerate=16000,
            blocksize=3000, #change for buffer lenght
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._audio_callback
        ):
            while not self._stop_event.is_set():
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        # Print the recognized text to the console
                        print(f"Recognized: {text}")  # print to stdout
                        self.callback(text)
                else:
                    # Optionally print partial results
                    partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
                    if partial:
                        print(f"Partial: {partial}", end="\r")  # overwrite line
                        self.partial_callback(partial)

        print("VoiceRecognizer stopped listening")  # notify stop

    def start(self):
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        del self.model; gc.collect()
        self._stop_event.set()
        self.thread.join()
        gc.collect()
        print("VoiceRecognizer thread joined")  # final join message
