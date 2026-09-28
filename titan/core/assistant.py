"""Coordonează parserul, confirmările și acțiunile Windows."""

from __future__ import annotations

from titan.core.command_router import Action, Command, CommandRouter
from titan.tools.windows.actions import WindowsActions
from titan.tools.smart_home import SmartHomeActions
from titan.tools.whatsapp import WhatsAppContacts
from titan.tools.wake_on_lan import WakeOnLanActions


class TitanAssistant:
    def __init__(self) -> None:
        self.router = CommandRouter()
        self.windows = WindowsActions()
        self.smart_home = SmartHomeActions()
        self.wake_on_lan = WakeOnLanActions()
        self.whatsapp = WhatsAppContacts()
        self.pending_command: Command | None = None
        self.whatsapp_recipient: str | None = None
        self.whatsapp_draft_ready = False

    def handle(self, user_text: str) -> str:
        normalized = user_text.strip().lower()
        if self.pending_command:
            if normalized in {"da", "confirm", "confirma", "yes"}:
                command = self.pending_command
                self.pending_command = None
                response = self._execute(command)
                if command.action == Action.SEND_WHATSAPP_DRAFT:
                    self.whatsapp_draft_ready = True
                    return response + " Când vezi conversația corectă, spune «trimite»."
                return response
            if normalized in {"nu", "anuleaza", "anulează", "no"}:
                self.pending_command = None
                return "Am anulat acțiunea."
            return "Aștept confirmarea: spune «da» sau «nu»."

        if self.whatsapp_draft_ready:
            if normalized in {"trimite", "send", "trimite acum"}:
                self.whatsapp_draft_ready = False
                return self.windows.send_whatsapp_message()
            if normalized in {"nu", "anuleaza", "anulează", "cancel"}:
                self.whatsapp_draft_ready = False
                return "Am anulat mesajul WhatsApp; nu a fost trimis."

        if self.whatsapp_recipient:
            if normalized in {"nu", "anuleaza", "anulează", "cancel"}:
                self.whatsapp_recipient = None
                return "Am anulat mesajul WhatsApp."
            command = self.router.parse(user_text)
            if command.action == Action.SET_WHATSAPP_TEXT:
                message = str(command.arguments["message"])
                recipient = self.whatsapp_recipient
                self.whatsapp_recipient = None
                self.pending_command = Command(
                    Action.SEND_WHATSAPP_DRAFT,
                    {"contact": recipient, "message": message},
                    requires_confirmation=True,
                )
                return f"Confirmi mesajul către {recipient}: «{message}»? Spune «da» sau «nu»."
            return "Aștept textul mesajului. Spune, de exemplu: «textul ajung acasă în zece minute»."

        command = self.router.parse(user_text)
        if command.action == Action.UNKNOWN:
            return "Nu am înțeles încă această comandă. Încearcă, de exemplu: «deschide Chrome» sau «pune volumul la 30»."
        if command.action == Action.SEND_WHATSAPP_DRAFT:
            contact = str(command.arguments["contact"])
            message = str(command.arguments["message"])
            if not self.whatsapp.phone_for(contact):
                return (
                    f"Nu găsesc contactul «{contact}». Completează mai întâi contacts.json "
                    "cu un alias și numărul în format internațional."
                )
            self.pending_command = command
            self.whatsapp_draft_ready = False
            return f"Confirmi mesajul către {contact}: «{message}»? Spune «da» sau «nu»."
        if command.action == Action.START_WHATSAPP_MESSAGE:
            contact = str(command.arguments["contact"])
            if not self.whatsapp.phone_for(contact):
                return f"Nu găsesc contactul «{contact}» în contacts.json."
            self.whatsapp_recipient = contact
            return f"Pentru cineva numit {contact}. Care este textul mesajului?"
        if command.requires_confirmation:
            self.pending_command = command
            return "Această acțiune poate închide conținut nesalvat. Confirmi?"
        return self._execute(command)

    def _execute(self, command: Command) -> str:
        if command.action == Action.OPEN_APP:
            return self.windows.open_app(str(command.arguments["app"]))
        if command.action == Action.OPEN_URL:
            return self.windows.open_url(str(command.arguments["url"]))
        if command.action == Action.SEARCH_WEB:
            return self.windows.search_web(str(command.arguments["query"]))
        if command.action == Action.SET_VOLUME:
            if "adjustment" in command.arguments:
                return self.windows.adjust_volume(int(command.arguments["adjustment"]))
            return self.windows.set_volume(int(command.arguments["percent"]))
        if command.action == Action.MUTE:
            return self.windows.set_mute(True)
        if command.action == Action.UNMUTE:
            return self.windows.set_mute(False)
        if command.action == Action.TAKE_SCREENSHOT:
            return self.windows.take_screenshot()
        if command.action == Action.CONTROL_LIGHT:
            return self.smart_home.control(command.arguments)
        if command.action == Action.WAKE_LAPTOP:
            return self.wake_on_lan.wake()
        if command.action == Action.SEARCH_SPOTIFY:
            return self.windows.search_music(str(command.arguments["query"]))
        if command.action == Action.SEARCH_YOUTUBE:
            return self.windows.search_youtube(str(command.arguments["query"]))
        if command.action == Action.TOGGLE_PLAYBACK:
            return self.windows.toggle_playback()
        if command.action == Action.STOP_PLAYBACK:
            return self.windows.stop_playback()
        if command.action == Action.NEXT_TRACK:
            return self.windows.next_track()
        if command.action == Action.PREVIOUS_TRACK:
            return self.windows.previous_track()
        if command.action == Action.CLOSE_ACTIVE_WINDOW:
            return self.windows.close_active_window()
        if command.action == Action.CLOSE_CURRENT_TAB:
            return self.windows.close_current_tab()
        if command.action == Action.CLOSE_CHROME:
            return self.windows.close_chrome()
        if command.action == Action.CLOSE_SPOTIFY:
            return self.windows.close_spotify()
        if command.action == Action.OPEN_WHATSAPP:
            return self.windows.open_url("https://web.whatsapp.com")
        if command.action == Action.SEND_WHATSAPP_DRAFT:
            contact = str(command.arguments["contact"])
            message = str(command.arguments["message"])
            url = self.whatsapp.draft_url(contact, message)
            if not url:
                return f"Nu găsesc contactul «{contact}»."
            self.windows.open_url(url)
            return (
                f"Am deschis WhatsApp pentru {contact}, cu mesajul completat. "
                "Verifică destinatarul și apasă Trimite în WhatsApp."
            )
        return "Acțiunea nu este disponibilă."
