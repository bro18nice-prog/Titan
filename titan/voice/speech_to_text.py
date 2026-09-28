"""Recunoaștere vocală locală pentru comenzi scurte bilingve."""

from __future__ import annotations

from pathlib import Path


class SpeechToText:
    """Înregistrează o comandă și o transcrie fără a trimite audio în cloud."""

    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self.sample_rate = 16_000
        self._model = None
        self.models_dir = Path("models")

    def listen(self, seconds: int) -> str:
        """Ascultă până la liniște, fără să aștepte inutil durata maximă."""
        import numpy as np
        import sounddevice as sd
        print("[Microfon activ]")
        block_size = 1_024
        max_blocks = int(seconds * self.sample_rate / block_size)
        # O pauză de circa jumătate de secundă încheie o comandă scurtă.
        silent_blocks_to_stop = int(0.55 * self.sample_rate / block_size)
        chunks: list[np.ndarray] = []
        speech_started = False
        silent_blocks = 0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
        ) as stream:
            for _ in range(max_blocks):
                chunk, _overflowed = stream.read(block_size)
                chunks.append(chunk.copy())
                volume = float(np.sqrt(np.mean(np.square(chunk))))
                if volume > 0.012:
                    speech_started = True
                    silent_blocks = 0
                elif speech_started:
                    silent_blocks += 1
                    if silent_blocks >= silent_blocks_to_stop:
                        break

        if not speech_started:
            return ""
        audio = np.concatenate(chunks).reshape(-1)
        print("[Procesez comanda]")

        if self._model is None:
            from faster_whisper import WhisperModel

            self.models_dir.mkdir(exist_ok=True)
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(self.models_dir),
            )

        segments, _info = self._model.transcribe(
            audio,
            task="transcribe",
            vad_filter=True,
            beam_size=1,
            best_of=1,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=(
                "Comenzi foarte scurte pentru asistentul TITAN în română și engleză: "
                "deschide Google, pune volumul la 50, open Spotify, "
                "set volume to 50, play music, search Google weather."
            ),
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
