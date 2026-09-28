"""Transformă expresii simple în comenzi sigure pentru TITAN.

Nu ghicim acțiuni cu risc: o cerere neînțeleasă este refuzată politicos.
În etapa AI, modelul va folosi aceleași acțiuni, nu va executa cod liber.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from enum import StrEnum
import re
import unicodedata


class Action(StrEnum):
    OPEN_APP = "open_app"
    OPEN_URL = "open_url"
    SEARCH_WEB = "search_web"
    SET_VOLUME = "set_volume"
    MUTE = "mute"
    UNMUTE = "unmute"
    TAKE_SCREENSHOT = "take_screenshot"
    CONTROL_LIGHT = "control_light"
    WAKE_LAPTOP = "wake_laptop"
    SEARCH_SPOTIFY = "search_spotify"
    SEARCH_YOUTUBE = "search_youtube"
    TOGGLE_PLAYBACK = "toggle_playback"
    STOP_PLAYBACK = "stop_playback"
    NEXT_TRACK = "next_track"
    PREVIOUS_TRACK = "previous_track"
    CLOSE_ACTIVE_WINDOW = "close_active_window"
    CLOSE_CURRENT_TAB = "close_current_tab"
    CLOSE_CHROME = "close_chrome"
    CLOSE_SPOTIFY = "close_spotify"
    OPEN_WHATSAPP = "open_whatsapp"
    SEND_WHATSAPP_DRAFT = "send_whatsapp_draft"
    START_WHATSAPP_MESSAGE = "start_whatsapp_message"
    SET_WHATSAPP_TEXT = "set_whatsapp_text"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Command:
    action: Action
    arguments: dict[str, str | int] = field(default_factory=dict)
    requires_confirmation: bool = False


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    # Păstrăm punctul dintre două fragmente alfanumerice pentru adrese precum
    # wikipedia.org, dar eliminăm punctuația de final a propoziției.
    without_punctuation = re.sub(r"[,!?:;]+", " ", without_accents)
    without_punctuation = re.sub(r"(?<![a-z0-9])\.|\.(?![a-z0-9])", " ", without_punctuation)
    return " ".join(without_punctuation.split())


def _has_similar_word(text: str, expected_words: tuple[str, ...], cutoff: float = 0.78) -> bool:
    """Acceptă mici erori STT doar pentru intenții nepericuloase.

    De exemplu, Whisper poate transcrie „deschide” ca „deschidă”. Nu folosim
    această toleranță pentru ștergeri sau alte acțiuni sensibile.
    """
    words = re.findall(r"[a-z0-9]+", text)
    return any(get_close_matches(word, expected_words, n=1, cutoff=cutoff) for word in words)


_DIGIT_WORDS = {
    "zero": 0, "unu": 1, "una": 1, "doi": 2, "doua": 2, "trei": 3,
    "patru": 4, "cinci": 5, "sase": 6, "sapte": 7, "opt": 8, "noua": 9,
}
_TENS_WORDS = {
    "zece": 10, "douazeci": 20, "treizeci": 30, "patruzeci": 40,
    "cincizeci": 50, "saizeci": 60, "saptezeci": 70, "optzeci": 80,
    "nouazeci": 90, "o suta": 100, "suta": 100,
}


def _spoken_percent(value_text: str) -> int | None:
    """Înțelege atât 30, cât și „treizeci” ori „trei zero”."""
    digits = re.match(r"\s*(\d{1,3})", value_text)
    if digits:
        return int(digits.group(1))

    words = re.findall(r"[a-z0-9]+", value_text)
    if not words:
        return None
    first = words[0]
    if first in _TENS_WORDS:
        value = _TENS_WORDS[first]
        if len(words) > 1 and words[1] in _DIGIT_WORDS and value < 100:
            value += _DIGIT_WORDS[words[1]]
        return value
    if len(words) >= 2 and words[0] in _DIGIT_WORDS and words[1] == "zeci":
        value = _DIGIT_WORDS[words[0]] * 10
        if len(words) >= 3 and words[2] in _DIGIT_WORDS:
            value += _DIGIT_WORDS[words[2]]
        return value
    # Forma cea mai robustă pentru STT: „trei zero” = 30.
    digit_words: list[str] = []
    for word in words[:3]:
        if word not in _DIGIT_WORDS:
            break
        digit_words.append(str(_DIGIT_WORDS[word]))
    return int("".join(digit_words)) if digit_words else None


class CommandRouter:
    """Parser determinist pentru comenzile din prima versiune."""

    APPS = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "spotify": "spotify",
        "discord": "discord",
        "league of legends": "league_of_legends",
        "league": "league_of_legends",
        "lol": "league_of_legends",
        "counter strike": "counter_strike",
        "counter-strike": "counter_strike",
        "cs2": "counter_strike",
    }
    WEBSITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "spotify": "https://open.spotify.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "tiktok": "https://www.tiktok.com",
        "netflix": "https://www.netflix.com",
        "twitch": "https://www.twitch.tv",
        "reddit": "https://www.reddit.com",
        "wikipedia": "https://www.wikipedia.org",
    }

    def parse(self, user_text: str) -> Command:
        text = _normalize(user_text)
        wants_to_open = _has_similar_word(
            text,
            ("deschide", "porneste", "intra", "open", "launch", "start", "visit"),
        )

        if text in {"close google", "inchide google", "inchide chrome", "close chrome"}:
            return Command(Action.CLOSE_CHROME, requires_confirmation=True)
        if text in {"close spotify", "inchide spotify"}:
            return Command(Action.CLOSE_SPOTIFY, requires_confirmation=True)

        if text in {"intra pe whatsapp", "deschide whatsapp", "open whatsapp"}:
            return Command(Action.OPEN_WHATSAPP)

        whatsapp_match = re.fullmatch(r"trimite lui\s+(.+?)\s+(?:mesajul|mesaj)\s+(.+)", text)
        if whatsapp_match:
            return Command(
                Action.SEND_WHATSAPP_DRAFT,
                {"contact": whatsapp_match.group(1), "message": whatsapp_match.group(2)},
                requires_confirmation=True,
            )

        whatsapp_recipient_match = re.fullmatch(r"trimite mesaj(?:ul)? lui\s+(.+)", text)
        if whatsapp_recipient_match:
            return Command(
                Action.START_WHATSAPP_MESSAGE,
                {"contact": whatsapp_recipient_match.group(1)},
            )

        whatsapp_text_match = re.fullmatch(r"(?:textul|mesajul este|text)\s+(.+)", text)
        if whatsapp_text_match:
            return Command(Action.SET_WHATSAPP_TEXT, {"message": whatsapp_text_match.group(1)})
        if any(phrase in text for phrase in ("inchide tab", "close tab", "iesi din tab", "scoate tab", "gata cu tab")):
            return Command(Action.CLOSE_CURRENT_TAB, requires_confirmation=True)
        if any(phrase in text for phrase in (
            "inchide fereastra", "inchide aplicatia", "inchide pagina", "close window",
            "iesi din fereastra", "gata cu pagina", "scoate pagina",
        )):
            return Command(Action.CLOSE_ACTIVE_WINDOW, requires_confirmation=True)

        if text.startswith("close ") or text.startswith("inchide "):
            target = text.split(maxsplit=1)[1]
            if target in self.WEBSITES:
                # Fără extensie de browser nu citim lista de taburi. Închidem
                # conservator doar tabul activ, după confirmarea utilizatorului.
                return Command(Action.CLOSE_CURRENT_TAB, requires_confirmation=True)

        if text in {
            "play", "start", "resume", "start music", "play music", "play song",
            "da play", "porneste muzica", "porneste melodia", "pauza", "pause",
        }:
            return Command(Action.TOGGLE_PLAYBACK)
        if text in {
            "stop", "stop music", "stop song", "opreste muzica", "opreste melodia",
            "opreste music", "stopeaza", "gata muzica", "stopeste",
        } or _has_similar_word(text, ("stop",), cutoff=0.70):
            return Command(Action.STOP_PLAYBACK)
        if text in {"urmatoarea melodie", "melodia urmatoare", "next", "next song", "urmatoarea"}:
            return Command(Action.NEXT_TRACK)
        if text in {"melodia precedenta", "precedenta", "previous", "previous song", "inapoi la melodie"}:
            return Command(Action.PREVIOUS_TRACK)

        if text in {"mute", "muta", "fara sunet", "opreste sunetul", "taie sunetul"}:
            return Command(Action.MUTE)
        if text in {"unmute", "porneste sunetul", "activeaza sunetul", "da drumul la sunet"}:
            return Command(Action.UNMUTE)

        if text in {"screenshot", "captura ecran", "fa screenshot", "fă screenshot", "poza ecran"}:
            return Command(Action.TAKE_SCREENSHOT)

        if text in {
            "porneste laptopul", "porneste laptop", "deschide laptopul", "deschide laptop",
            "wake laptop", "wake up laptop", "turn on laptop", "start laptop",
        }:
            return Command(Action.WAKE_LAPTOP)

        volume_match = re.search(
            r"(?:volum(?:ul)?(?: la)?|pune volumul la|set volume(?: to)?)\s+(.+)",
            text,
        )
        if volume_match:
            value = _spoken_percent(volume_match.group(1))
            if value is not None and 0 <= value <= 100:
                return Command(Action.SET_VOLUME, {"percent": value})

        if text in {"mai tare", "da mai tare", "volume up", "volum mai tare"}:
            return Command(Action.SET_VOLUME, {"adjustment": 10})
        if text in {"mai incet", "mai încet", "da mai incet", "volume down", "volum mai incet"}:
            return Command(Action.SET_VOLUME, {"adjustment": -10})

        light_command = self._parse_light_command(text)
        if light_command:
            return light_command

        youtube_match = re.search(r"(?:pune pe youtube|cauta pe youtube|search youtube)\s+(.+)", text)
        if youtube_match:
            return Command(Action.SEARCH_YOUTUBE, {"query": youtube_match.group(1)})

        spotify_explicit_match = re.search(r"(?:pune pe spotify|cauta pe spotify|search spotify)\s+(.+)", text)
        if spotify_explicit_match:
            return Command(Action.SEARCH_SPOTIFY, {"query": spotify_explicit_match.group(1)})

        spotify_match = re.search(
            r"(?:cauta pe spotify|search spotify|pune (?:melodia|muzica)|pune|play song|play music|"
            r"porneste (?:melodia|muzica)|start song|start music)\s+(.+)",
            text,
        )
        if spotify_match:
            return Command(Action.SEARCH_SPOTIFY, {"query": spotify_match.group(1)})

        search_match = re.search(
            r"(?:cauta(?: pe (?:internet|google))?|cauta mi|search(?: (?:the )?(?:web|internet|google))?)\s+(.+)",
            text,
        )
        if search_match:
            query = re.sub(r"\s+(?:pe google|on google)$", "", search_match.group(1)).strip()
            return Command(Action.SEARCH_WEB, {"query": query})

        visit_match = re.fullmatch(r"(?:intra pe|visit)\s+([a-z0-9-]+\.[a-z]{2,}(?:/[a-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?)", text)
        if visit_match:
            domain = visit_match.group(1)
            return Command(Action.OPEN_URL, {"url": f"https://{domain}"})

        for app_name, app_id in self.APPS.items():
            app_is_mentioned = app_name in text or _has_similar_word(text, (app_name,), cutoff=0.70)
            if wants_to_open and app_is_mentioned:
                return Command(Action.OPEN_APP, {"app": app_id})

        for website_name, url in self.WEBSITES.items():
            if wants_to_open and website_name in text:
                return Command(Action.OPEN_URL, {"url": url})

        # Potrivirea aproximativă este doar fallback; întâi preferăm mereu un
        # nume exact (de pildă TikTok nu trebuie confundat cu Instagram).
        for website_name, url in self.WEBSITES.items():
            if wants_to_open and _has_similar_word(text, (website_name,), cutoff=0.70):
                return Command(Action.OPEN_URL, {"url": url})

        unknown_visit = re.fullmatch(r"intra pe\s+(.+)", text)
        if unknown_visit:
            return Command(Action.SEARCH_WEB, {"query": unknown_visit.group(1)})

        return Command(Action.UNKNOWN)

    @staticmethod
    def _parse_light_command(text: str) -> Command | None:
        """Comenzi locale pentru Home Assistant; nu acceptă cod sau nume libere."""
        words = set(re.findall(r"[a-z0-9]+", text))
        mentions_light = any(
            word.startswith(("lumin", "led", "bec", "light"))
            for word in words
        )
        # "turn on/off" este suficient de explicit şi e mai uşor de recunoscut
        # de transcriere decât echivalentul românesc. Îl acceptăm şi fără
        # cuvântul "bec", de exemplu: "turn off pe hol".
        english_power_command = "turn on" in text or "turn off" in text
        if not mentions_light and not english_power_command:
            return None

        room = "all"
        room_words = {
            "bucatarie": "bucatarie", "kitchen": "bucatarie",
            "hol": "hol", "hall": "hol",
            "dormitor": "dormitor", "bedroom": "dormitor",
            "camera": "camera", "room": "camera",
            "birou": "birou", "office": "birou",
            "living": "living", "bathroom": "baie", "baie": "baie",
        }
        for candidate, configured_room in room_words.items():
            if candidate in text:
                room = configured_room
                break

        if words & {"stinge", "opreste", "off"} or "turn off" in text:
            return Command(Action.CONTROL_LIGHT, {"operation": "off", "room": room})
        if words & {"aprinde", "porneste", "deschide", "on"} or "turn on" in text:
            return Command(Action.CONTROL_LIGHT, {"operation": "on", "room": room})

        brightness = re.search(
            r"(?:lumina|lumini|leduri|led|intensitate|brightness)\b(?:\s+(?!la\b|to\b)\w+){0,4}\s+(?:la|to)\s*(\d{1,3})\s*%?",
            text,
        )
        if not brightness:
            brightness = re.search(
                r"(?:lumina|lumini|leduri|led|intensitate|brightness)(?:\s+(?:la|to))?\s*(\d{1,3})\s*%?",
                text,
            )
        if brightness and 0 <= int(brightness.group(1)) <= 100:
            return Command(
                Action.CONTROL_LIGHT,
                {"operation": "brightness", "room": room, "percent": int(brightness.group(1))},
            )

        colors = {
            "ros": "red", "red": "red",
            "albastr": "blue", "blue": "blue",
            "verd": "green", "green": "green",
            "mov": "purple", "purple": "purple", "violet": "purple",
            "galben": "yellow", "yellow": "yellow",
            "alb": "white", "white": "white",
            "cald": "warm_white", "warm": "warm_white",
            "rece": "cool_white", "cool": "cool_white",
        }
        for spoken_color, color in colors.items():
            if spoken_color in text:
                return Command(Action.CONTROL_LIGHT, {"operation": "color", "room": room, "color": color})
        return None
