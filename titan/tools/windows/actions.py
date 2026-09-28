"""Acțiuni Windows strict limitate, utilizate de TITAN.

Acest modul este singurul loc în care nucleul poate controla Windows. Când
adăugăm Raspberry Pi, acesta va primi un modul echivalent, separat.
"""

from __future__ import annotations

from ctypes import windll
from pathlib import Path
from datetime import datetime
import os
import subprocess
from urllib.parse import quote, quote_plus
import webbrowser


class WindowsActions:
    def __init__(self) -> None:
        # Reținem local doar dacă TITAN a deschis YouTube în sesiunea curentă.
        # Nu citim istoricul sau taburile utilizatorului.
        self._youtube_opened_by_titan = False

    def open_app(self, app: str) -> str:
        if app == "chrome":
            chrome = self._chrome_path()
            if not chrome:
                # Pe acest calculator Chrome nu apare în locațiile sau registrul
                # Windows obișnuite. Păstrăm comanda utilă prin browserul implicit.
                webbrowser.open_new_tab("https://www.google.com")
                return "Nu am găsit Chrome instalat. Am deschis o pagină în browserul implicit."
            subprocess.Popen([str(chrome)])
            return "Deschid Chrome."

        if app == "spotify":
            # URI-ul este gestionat de aplicația Spotify dacă aceasta este instalată.
            try:
                os.startfile("spotify:")
                return "Deschid Spotify."
            except OSError:
                return "Nu am găsit aplicația Spotify. Instaleaz-o, apoi încearcă din nou."

        if app == "discord":
            try:
                os.startfile("discord:")
                return "Deschid Discord."
            except OSError:
                return "Nu am găsit Discord instalat."

        if app == "counter_strike":
            try:
                os.startfile("steam://rungameid/730")
                return "Pornesc Counter-Strike din Steam."
            except OSError:
                return "Nu am găsit Steam. Deschide Steam și verifică dacă Counter-Strike este instalat."

        if app == "league_of_legends":
            league_paths = [
                Path("C:/Riot Games/League of Legends/LeagueClient.exe"),
                Path("D:/Riot Games/League of Legends/LeagueClient.exe"),
            ]
            league = next((path for path in league_paths if path.is_file()), None)
            if league:
                subprocess.Popen([str(league)])
                return "Pornesc League of Legends."
            return "Nu am găsit League of Legends în C: sau D:. Îl putem adăuga dintr-o locație aleasă de tine."

        return "Aplicația cerută nu este disponibilă încă."

    def open_url(self, url: str) -> str:
        if "youtube.com" in url:
            self._youtube_opened_by_titan = True
        self._open_browser_url(url)
        return "Deschid pagina cerută."

    def search_web(self, query: str) -> str:
        self._open_browser_url(f"https://www.google.com/search?q={quote_plus(query)}")
        return f"Caut pe internet: {query}."

    @staticmethod
    def _chrome_path() -> Path | None:
        chrome_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        return next((path for path in chrome_paths if path.is_file()), None)

    def _open_browser_url(self, url: str) -> None:
        """Preferă Chrome pentru comenzi vocale; păstrează fallback sigur."""
        chrome = self._chrome_path()
        if chrome:
            subprocess.Popen([str(chrome), url])
            return
        webbrowser.open_new_tab(url)

    def search_spotify(self, query: str) -> str:
        try:
            os.startfile(f"spotify:search:{quote(query)}")
            return f"Caut în Spotify: {query}."
        except OSError:
            return "Nu am găsit aplicația Spotify. Instaleaz-o, apoi încearcă din nou."

    def search_youtube(self, query: str) -> str:
        self._youtube_opened_by_titan = True
        self._open_browser_url(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
        return f"Caut pe YouTube: {query}."

    def search_music(self, query: str) -> str:
        """YouTube are prioritate dacă TITAN l-a deschis și Chrome este activ."""
        if self._youtube_opened_by_titan and self._is_process_running("chrome.exe"):
            return self.search_youtube(query)
        return self.search_spotify(query)

    @staticmethod
    def _is_process_running(process_name: str) -> bool:
        try:
            completed = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return process_name.lower() in completed.stdout.lower()
        except OSError:
            return False

    def set_volume(self, percent: int) -> str:
        try:
            volume = self._endpoint_volume()
            volume.SetMasterVolumeLevelScalar(percent / 100, None)
            return f"Am setat volumul la {percent}%."
        except ImportError:
            return "Controlul volumului necesită dependențele proiectului. Rulează întâi instalarea din README."
        except Exception:
            return "Nu am putut modifica volumul. Verifică dacă dispozitivul audio este disponibil."

    def adjust_volume(self, adjustment: int) -> str:
        try:
            current = round(self._endpoint_volume().GetMasterVolumeLevelScalar() * 100)
            return self.set_volume(max(0, min(100, current + adjustment)))
        except ImportError:
            return "Controlul volumului necesită dependențele proiectului."
        except Exception:
            return "Nu am putut modifica volumul. Verifică dispozitivul audio."

    def set_mute(self, muted: bool) -> str:
        try:
            self._endpoint_volume().SetMute(1 if muted else 0, None)
            return "Am oprit sunetul." if muted else "Am pornit sunetul."
        except ImportError:
            return "Controlul audio necesită dependențele proiectului."
        except Exception:
            return "Nu am putut modifica sunetul. Verifică dispozitivul audio."

    @staticmethod
    def _endpoint_volume():
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        return device.EndpointVolume

    def take_screenshot(self) -> str:
        try:
            from PIL import ImageGrab

            screenshots = Path("screenshots")
            screenshots.mkdir(exist_ok=True)
            filename = screenshots / f"titan-{datetime.now():%Y%m%d-%H%M%S}.png"
            ImageGrab.grab().save(filename)
            return f"Am salvat screenshot-ul: {filename}."
        except ImportError:
            return "Pentru screenshot instalează dependențele TITAN actualizate."
        except Exception:
            return "Nu am putut face screenshot-ul."

    def close_active_window(self) -> str:
        # Alt+F4 trimite cererea normală de închidere; aplicația poate cere salvare.
        windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt apăsat
        windll.user32.keybd_event(0x73, 0, 0, 0)  # F4 apăsat
        windll.user32.keybd_event(0x73, 0, 2, 0)  # F4 eliberat
        windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt eliberat
        return "Am trimis cererea de închidere pentru fereastra activă."

    def close_current_tab(self) -> str:
        # Ctrl+W este executat numai după confirmare, deoarece poate închide conținut activ.
        windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl apăsat
        windll.user32.keybd_event(0x57, 0, 0, 0)  # W apăsat
        windll.user32.keybd_event(0x57, 0, 2, 0)  # W eliberat
        windll.user32.keybd_event(0x11, 0, 2, 0)  # Ctrl eliberat
        return "Am închis tabul activ."

    def close_chrome(self) -> str:
        return self._close_process("chrome.exe", "Am cerut Chrome să închidă toate ferestrele și taburile.")

    def close_spotify(self) -> str:
        return self._close_process("Spotify.exe", "Am cerut Spotify să se închidă.")

    def send_whatsapp_message(self) -> str:
        """Activează tabul WhatsApp Web pregătit și trimite Enter.

        Este apelată numai după confirmarea explicită a mesajului și comanda
        separată „trimite”. Dacă nu găsim WhatsApp, nu apăsăm taste în altă
        aplicație.
        """
        if not self._focus_window_containing("whatsapp"):
            return "Nu găsesc fereastra WhatsApp. Deschide conversația pregătită și spune din nou «trimite»."
        self._press_key(0x0D)  # VK_RETURN: butonul Send din WhatsApp Web
        return "Am trimis mesajul WhatsApp confirmat."

    @staticmethod
    def _close_process(process_name: str, success_message: str) -> str:
        """Cere închiderea normală, fără /F, pentru a nu forța date nesalvate."""
        try:
            completed = subprocess.run(
                ["taskkill", "/IM", process_name],
                capture_output=True,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if completed.returncode == 0:
                return success_message
            return f"Nu am găsit aplicația {process_name} deschisă."
        except OSError:
            return f"Nu am putut închide aplicația {process_name}."

    def toggle_playback(self) -> str:
        self._press_media_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
        return "Am trimis comanda play/pause către playerul activ."

    def stop_playback(self) -> str:
        """Folosește comanda media Stop, nu Play/Pause."""
        self._press_media_key(0xB2)  # VK_MEDIA_STOP
        return "Am oprit redarea media."

    def next_track(self) -> str:
        self._press_media_key(0xB0)  # VK_MEDIA_NEXT_TRACK
        return "Am trecut la următoarea melodie."

    def previous_track(self) -> str:
        self._press_media_key(0xB1)  # VK_MEDIA_PREV_TRACK
        return "Am revenit la melodia precedentă."

    @staticmethod
    def _press_media_key(virtual_key: int) -> None:
        """Trimite o tastă multimedia Windows, fără a depinde de fereastra Spotify."""
        windll.user32.keybd_event(virtual_key, 0, 0, 0)
        windll.user32.keybd_event(virtual_key, 0, 2, 0)

    @staticmethod
    def _press_key(virtual_key: int) -> None:
        windll.user32.keybd_event(virtual_key, 0, 0, 0)
        windll.user32.keybd_event(virtual_key, 0, 2, 0)

    @staticmethod
    def _focus_window_containing(expected_title: str) -> bool:
        """Găsește doar ferestre vizibile cu titlul WhatsApp din Chrome."""
        from ctypes import WINFUNCTYPE, byref, c_bool, c_int, create_unicode_buffer
        from ctypes.wintypes import HWND, LPARAM

        user32 = windll.user32
        found: list[int] = []

        @WINFUNCTYPE(c_bool, HWND, LPARAM)
        def visit_window(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if not length:
                return True
            title = create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if expected_title in title.value.lower():
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(visit_window, 0)
        if not found:
            return False
        user32.ShowWindow(found[0], 9)  # SW_RESTORE
        return bool(user32.SetForegroundWindow(found[0]))
