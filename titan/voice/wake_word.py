"""Wake word local, gratuit, pentru cuvântul „Titan”, bazat pe Vosk."""

from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import json


class WakeWordNotConfiguredError(RuntimeError):
    """Modelul local gratuit lipsește din folderul proiectului."""


class WakeWordListener:
    """Detectează numai „Titan”; nu trimite audio pe internet."""

    def __init__(self) -> None:
        self._stream = None
        self._detections: Queue[bool] = Queue()

    def start(self) -> None:
        model_path = Path("models/vosk-model-small-en-us-0.15")
        if not model_path.is_dir():
            raise WakeWordNotConfiguredError(f"Lipsește modelul local Vosk: {model_path}.")

        import sounddevice as sd
        from vosk import KaldiRecognizer, Model, SetLogLevel

        SetLogLevel(-1)
        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, 16_000, '["titan", "[unk]"]')

        def audio_callback(indata, _frames, _time, status) -> None:
            if status:
                return
            accepted = recognizer.AcceptWaveform(bytes(indata))
            result = recognizer.Result() if accepted else recognizer.PartialResult()
            payload = json.loads(result)
            transcript = payload.get("text", "") or payload.get("partial", "")
            if "titan" in transcript.lower():
                self._detections.put(True)
                recognizer.Reset()

        self._stream = sd.RawInputStream(
            samplerate=16_000,
            blocksize=4_000,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )
        self._stream.start()

    def detected(self) -> bool:
        try:
            self._detections.get_nowait()
            return True
        except Empty:
            return False

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
