# voice.py
import threading
import speech_recognition as sr

class VoiceRecognizer:
    def __init__(self, callback):
        """
        callback(phrase: str)
        """
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.callback = callback
        self._stop_event = threading.Event()

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while not self._stop_event.is_set():
                try:
                    audio = self.recognizer.listen(source, timeout=1)
                    phrase = self.recognizer.recognize_google(audio)
                    self.callback(phrase.lower())
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    print(f"Voice error: {e}")

    def start(self):
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        self.thread.join()
