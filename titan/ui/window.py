"""Fereastră Start/Stop pentru ascultarea locală a lui TITAN."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext

from titan.core.assistant import TitanAssistant
from titan.voice.speaker import Speaker
from titan.voice.speech_to_text import SpeechToText
from titan.voice.wake_word import WakeWordListener, WakeWordNotConfiguredError


class TitanWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TITAN — Asistent local")
        self.root.geometry("720x660")
        self.root.minsize(650, 570)
        self.root.configure(bg="#0b1220")
        self.root.protocol("WM_DELETE_WINDOW", self.stop_and_close)
        self.assistant = TitanAssistant()
        self.speaker = Speaker()
        self.speech_to_text = SpeechToText()
        self.wake_word = WakeWordListener()
        self.is_listening = False
        self.in_conversation = False
        self.stop_requested = False
        self.wake_mode = "local"
        self.status = tk.StringVar(value="TITAN nu mai ascultă")
        self._build_layout()

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg="#0b1220")
        header.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(header, text="TITAN", font=("Segoe UI", 32, "bold"), fg="#6ee7ff", bg="#0b1220").pack(anchor="w")
        tk.Label(header, text="ASISTENT LOCAL • FĂRĂ API • CONTROL LIMITAT ȘI SIGUR", font=("Segoe UI", 9, "bold"), fg="#7e94b7", bg="#0b1220").pack(anchor="w", pady=(0, 10))

        status_card = tk.Frame(self.root, bg="#15243a", highlightbackground="#285071", highlightthickness=1)
        status_card.pack(fill="x", padx=28, pady=(0, 14))
        tk.Label(status_card, text="STARE", font=("Segoe UI", 9, "bold"), fg="#7e94b7", bg="#15243a").pack(anchor="w", padx=16, pady=(10, 0))
        self.status_label = tk.Label(status_card, textvariable=self.status, font=("Segoe UI", 13, "bold"), fg="#d9e2f1", bg="#15243a")
        self.status_label.pack(anchor="w", padx=16, pady=(2, 11))

        controls = tk.Frame(self.root, bg="#0b1220")
        controls.pack(pady=2)
        self.start_button = tk.Button(controls, text="START — ASCULTĂ «TITAN»", command=self.start_listening, font=("Segoe UI", 10, "bold"), bg="#117a8b", activebackground="#1595aa", fg="white", padx=16, pady=10, borderwidth=0)
        self.start_button.grid(row=0, column=0, padx=5)
        self.stop_button = tk.Button(controls, text="OPREȘTE", command=self.stop_listening, font=("Segoe UI", 10, "bold"), bg="#9d3144", activebackground="#bb3d54", fg="white", padx=16, pady=10, borderwidth=0, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)
        tk.Button(controls, text="TEST VOCE", command=self.test_voice_command, font=("Segoe UI", 10, "bold"), bg="#34445d", fg="white", padx=14, pady=10, borderwidth=0).grid(row=0, column=2, padx=5)

        quick = tk.Frame(self.root, bg="#0b1220")
        quick.pack(fill="x", padx=28, pady=(14, 6))
        tk.Label(quick, text="COMENZI RAPIDE", font=("Segoe UI", 9, "bold"), fg="#7e94b7", bg="#0b1220").pack(anchor="w", pady=(0, 6))
        buttons = (("Chrome", "deschide chrome"), ("YouTube", "intra pe youtube"), ("Spotify", "deschide spotify"), ("WhatsApp", "deschide whatsapp"), ("Play / Stop", "play"), ("Vol +", "mai tare"), ("Screenshot", "fa screenshot"))
        for index, (label, command) in enumerate(buttons):
            tk.Button(quick, text=label, command=lambda value=command: self._submit_command(value), font=("Segoe UI", 9, "bold"), bg="#1b2b43", activebackground="#294363", fg="#e5f2ff", padx=9, pady=7, borderwidth=0).pack(side="left", padx=(0, 6))

        command_frame = tk.Frame(self.root, bg="#0b1220")
        command_frame.pack(fill="x", padx=28, pady=(8, 12))
        self.command_entry = tk.Entry(command_frame, font=("Segoe UI", 12), bg="#15243a", fg="#f1f7ff", insertbackground="#f1f7ff", relief="flat")
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.command_entry.insert(0, "Scrie o comandă pentru TITAN...")
        self.command_entry.bind("<FocusIn>", self._clear_command_hint)
        self.command_entry.bind("<Return>", self._submit_typed_command)
        tk.Button(command_frame, text="EXECUTĂ", command=self._submit_typed_command, font=("Segoe UI", 10, "bold"), bg="#ff8a65", activebackground="#ff9f80", fg="#10151f", padx=14, pady=8, borderwidth=0).pack(side="left", padx=(8, 0))

        tk.Label(self.root, text="ACTIVITATE", font=("Segoe UI", 9, "bold"), fg="#7e94b7", bg="#0b1220").pack(anchor="w", padx=28, pady=(0, 5))
        self.log = scrolledtext.ScrolledText(self.root, height=9, wrap="word", font=("Consolas", 10), bg="#101b2d", fg="#dcecff", insertbackground="#dcecff", borderwidth=0, state="disabled")
        self.log.pack(fill="both", expand=True, padx=28, pady=(0, 22))
        self._write("TITAN este pregătit. Apasă Start, apoi spune «Titan» pentru o comandă.")

    def run(self) -> None:
        self.root.after(100, self._poll_wake_word)
        self.root.mainloop()

    def _write(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_command_hint(self, _event: object) -> None:
        if self.command_entry.get() == "Scrie o comandă pentru TITAN...":
            self.command_entry.delete(0, "end")

    def _submit_typed_command(self, _event: object | None = None) -> None:
        self._submit_command(self.command_entry.get())

    def _submit_command(self, command: str) -> None:
        command = command.strip()
        if not command or command == "Scrie o comandă pentru TITAN...":
            return
        self.command_entry.delete(0, "end")
        self._write(f"Tu: {command}")
        response = self.assistant.handle(command)
        self._write(f"TITAN: {response}")

    def start_listening(self) -> None:
        if self.is_listening:
            return
        try:
            self.wake_word.start()
            self.wake_mode = "porcupine"
        except WakeWordNotConfiguredError as error:
            self.status.set("TITAN nu mai ascultă — wake word neconfigurat")
            self._write(
                "Wake word-ul nu este configurat. Modul experimental local a fost oprit "
                "fiindcă retranscria continuu microfonul și consuma inutil resurse."
            )
            self._write(f"Detaliu: {error}")
            return
        except Exception as error:
            self.status.set("Nu pot porni microfonul")
            self._write(f"Eroare: {error}")
            return
        self.is_listening = True
        self.stop_requested = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.set("TITAN nu mai ascultă comenzi — spune «Titan»")
        self._write("Ascult doar wake word-ul «Titan». Nu procesez alte vorbe până nu îl spui.")

    def stop_listening(self) -> None:
        self.stop_requested = True
        self.is_listening = False
        self.in_conversation = False
        self.wake_word.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status.set("TITAN nu mai ascultă")
        self._write("TITAN a fost oprit.")

    def _poll_wake_word(self) -> None:
        if self.is_listening and not self.in_conversation and self.wake_word.detected():
            self.in_conversation = True
            self._begin_conversation("")
        self.root.after(100, self._poll_wake_word)

    def _begin_conversation(self, initial_command: str) -> None:
        if self.wake_mode == "porcupine":
            self.wake_word.stop()
        self.status.set("Vorbește acum")
        self._write("Wake word detectat. Vorbește acum — ai o singură comandă.")
        threading.Thread(target=self._run_conversation, kwargs={"initial_command": initial_command}, daemon=True).start()

    def test_voice_command(self) -> None:
        if self.in_conversation:
            return
        self.in_conversation = True
        self.stop_requested = False
        self.status.set("Vorbește acum")
        threading.Thread(target=self._run_conversation, kwargs={"single_turn": True}, daemon=True).start()

    def _run_conversation(self, single_turn: bool = False, initial_command: str = "") -> None:
        """Execută exact o comandă după wake word, apoi revine în repaus."""
        if self.stop_requested:
            return
        transcript = initial_command
        if not transcript:
            try:
                transcript = self.speech_to_text.listen(seconds=5)
            except Exception as error:
                self.root.after(0, lambda: self._write(f"Eroare microfon: {error}"))
                transcript = ""

        if transcript:
            self.root.after(0, lambda text=transcript: self._write(f"Tu: {text}"))
            if transcript.lower().strip() not in {"opreste te", "opreste titan", "titan opreste te"}:
                response = self.assistant.handle(transcript)
                self.root.after(0, lambda text=response: self._write(f"TITAN: {text}"))
                # Wake word-ul este repornit numai după ce TTS a terminat;
                # TITAN nu își va activa singur microfonul din propria voce.
                self.speaker.say(response)
        self.root.after(0, self._resume_after_conversation)

    def _resume_after_conversation(self) -> None:
        self.in_conversation = False
        if not self.is_listening or self.stop_requested:
            self.stop_listening()
            return
        try:
            self.wake_word.start()
            self.status.set("TITAN nu mai ascultă comenzi — spune «Titan»")
            self._write("Comanda s-a terminat. Spune «Titan» pentru următoarea comandă.")
        except Exception as error:
            self._write(f"Nu pot relua wake word-ul: {error}")
            self.stop_listening()

    def stop_and_close(self) -> None:
        self.stop_listening()
        self.root.destroy()
