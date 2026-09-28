import unittest

from titan.core.command_router import Action, CommandRouter


class CommandRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CommandRouter()

    def test_opens_chrome(self) -> None:
        command = self.router.parse("Titan, deschide Chrome")

        self.assertEqual(command.action, Action.OPEN_APP)
        self.assertEqual(command.arguments, {"app": "chrome"})

    def test_understands_a_slightly_misheard_open_command(self) -> None:
        command = self.router.parse("Deschidă Spotify")

        self.assertEqual(command.action, Action.OPEN_APP)
        self.assertEqual(command.arguments, {"app": "spotify"})

    def test_understands_a_slightly_misspelled_app_name(self) -> None:
        command = self.router.parse("Deschide Spotifai")

        self.assertEqual(command.action, Action.OPEN_APP)
        self.assertEqual(command.arguments, {"app": "spotify"})

    def test_understands_natural_chrome_request(self) -> None:
        command = self.router.parse("Deschide o pagină Chrome")

        self.assertEqual(command.action, Action.OPEN_APP)
        self.assertEqual(command.arguments, {"app": "chrome"})

    def test_opens_google(self) -> None:
        command = self.router.parse("Deschide Google")

        self.assertEqual(command.action, Action.OPEN_URL)
        self.assertEqual(command.arguments, {"url": "https://www.google.com"})

    def test_searches_google_naturally(self) -> None:
        command = self.router.parse("Caută pe Google vremea mâine")

        self.assertEqual(command.action, Action.SEARCH_WEB)
        self.assertEqual(command.arguments, {"query": "vremea maine"})

    def test_searches_a_song_in_spotify(self) -> None:
        command = self.router.parse("Pune melodia Blinding Lights")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "blinding lights"})

    def test_put_command_searches_a_song_in_spotify(self) -> None:
        command = self.router.parse("Pune Blinding Lights")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "blinding lights"})

    def test_song_search_ignores_terminal_punctuation(self) -> None:
        command = self.router.parse("Pune Oamenii.")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "oamenii"})

    def test_song_search_ignores_punctuation_after_command(self) -> None:
        command = self.router.parse("Pune, Creep!")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "creep"})

    def test_playback_command(self) -> None:
        command = self.router.parse("Dă play")

        self.assertEqual(command.action, Action.TOGGLE_PLAYBACK)

    def test_stop_pauses_the_active_player(self) -> None:
        command = self.router.parse("Stop")

        self.assertEqual(command.action, Action.STOP_PLAYBACK)

    def test_understands_a_misheard_stop_command(self) -> None:
        command = self.router.parse("Stopeaza")

        self.assertEqual(command.action, Action.STOP_PLAYBACK)

    def test_english_start_resumes_media(self) -> None:
        command = self.router.parse("Start")

        self.assertEqual(command.action, Action.TOGGLE_PLAYBACK)

    def test_english_song_request_searches_spotify(self) -> None:
        command = self.router.parse("Play song Blinding Lights")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "blinding lights"})

    def test_explicit_youtube_song_request(self) -> None:
        command = self.router.parse("Pune pe YouTube Creep Radiohead")

        self.assertEqual(command.action, Action.SEARCH_YOUTUBE)
        self.assertEqual(command.arguments, {"query": "creep radiohead"})

    def test_explicit_spotify_song_request(self) -> None:
        command = self.router.parse("Pune pe Spotify My Way Limp Bizkit")

        self.assertEqual(command.action, Action.SEARCH_SPOTIFY)
        self.assertEqual(command.arguments, {"query": "my way limp bizkit"})

    def test_english_google_search(self) -> None:
        command = self.router.parse("Search Google weather tomorrow")

        self.assertEqual(command.action, Action.SEARCH_WEB)
        self.assertEqual(command.arguments, {"query": "weather tomorrow"})

    def test_english_volume_command(self) -> None:
        command = self.router.parse("Set volume to 35")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"percent": 35})

    def test_sets_volume(self) -> None:
        command = self.router.parse("Pune volumul la 30%")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"percent": 30})

    def test_short_volume_command(self) -> None:
        command = self.router.parse("Volum 45")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"percent": 45})

    def test_understands_spoken_tens_volume(self) -> None:
        command = self.router.parse("Volum treizeci")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"percent": 30})

    def test_understands_digit_by_digit_volume(self) -> None:
        command = self.router.parse("Volum trei zero")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"percent": 30})

    def test_understands_volume_up(self) -> None:
        command = self.router.parse("Mai tare")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"adjustment": 10})

    def test_understands_volume_down(self) -> None:
        command = self.router.parse("Mai încet")

        self.assertEqual(command.action, Action.SET_VOLUME)
        self.assertEqual(command.arguments, {"adjustment": -10})

    def test_understands_mute_command(self) -> None:
        command = self.router.parse("Oprește sunetul")

        self.assertEqual(command.action, Action.MUTE)

    def test_understands_screenshot_command(self) -> None:
        command = self.router.parse("Fă screenshot")

        self.assertEqual(command.action, Action.TAKE_SCREENSHOT)

    def test_opens_counter_strike(self) -> None:
        command = self.router.parse("Deschide CS2")

        self.assertEqual(command.action, Action.OPEN_APP)
        self.assertEqual(command.arguments, {"app": "counter_strike"})

    def test_turns_lights_on(self) -> None:
        command = self.router.parse("Aprinde luminile din dormitor")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "on", "room": "dormitor"})

    def test_opens_kitchen_bulb_with_user_wording(self) -> None:
        command = self.router.parse("Deschide becul la bucătărie")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "on", "room": "bucatarie"})

    def test_prepares_wake_on_lan_for_laptop(self) -> None:
        command = self.router.parse("Pornește laptopul")

        self.assertEqual(command.action, Action.WAKE_LAPTOP)

    def test_prepares_wake_on_lan_in_english(self) -> None:
        command = self.router.parse("Wake laptop")

        self.assertEqual(command.action, Action.WAKE_LAPTOP)

    def test_turn_off_hall_light_in_english(self) -> None:
        command = self.router.parse("Turn off pe hol")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "off", "room": "hol"})

    def test_changes_light_color(self) -> None:
        command = self.router.parse("Pune luminile albastre în birou")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "color", "room": "birou", "color": "blue"})

    def test_changes_kitchen_light_color_in_english(self) -> None:
        command = self.router.parse("Red light in kitchen")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "color", "room": "bucatarie", "color": "red"})

    def test_changes_light_brightness(self) -> None:
        command = self.router.parse("Lumina din living la 40%")

        self.assertEqual(command.action, Action.CONTROL_LIGHT)
        self.assertEqual(command.arguments, {"operation": "brightness", "room": "living", "percent": 40})

    def test_closing_tab_requires_confirmation(self) -> None:
        command = self.router.parse("Închide tabul")

        self.assertEqual(command.action, Action.CLOSE_CURRENT_TAB)
        self.assertTrue(command.requires_confirmation)

    def test_close_tab_has_english_alternative(self) -> None:
        command = self.router.parse("Close tab")

        self.assertEqual(command.action, Action.CLOSE_CURRENT_TAB)
        self.assertTrue(command.requires_confirmation)

    def test_close_window_has_romanian_alternative(self) -> None:
        command = self.router.parse("Gata cu pagina")

        self.assertEqual(command.action, Action.CLOSE_ACTIVE_WINDOW)
        self.assertTrue(command.requires_confirmation)

    def test_close_google_closes_chrome(self) -> None:
        command = self.router.parse("Close Google")

        self.assertEqual(command.action, Action.CLOSE_CHROME)
        self.assertTrue(command.requires_confirmation)

    def test_close_spotify_closes_its_app(self) -> None:
        command = self.router.parse("Close Spotify")

        self.assertEqual(command.action, Action.CLOSE_SPOTIFY)
        self.assertTrue(command.requires_confirmation)

    def test_close_youtube_closes_only_active_tab(self) -> None:
        command = self.router.parse("Close YouTube")

        self.assertEqual(command.action, Action.CLOSE_CURRENT_TAB)
        self.assertTrue(command.requires_confirmation)

    def test_search_query(self) -> None:
        command = self.router.parse("Caută pe internet vremea în București")

        self.assertEqual(command.action, Action.SEARCH_WEB)
        self.assertEqual(command.arguments, {"query": "vremea in bucuresti"})

    def test_short_search_command(self) -> None:
        command = self.router.parse("Caută rețete de paste")

        self.assertEqual(command.action, Action.SEARCH_WEB)
        self.assertEqual(command.arguments, {"query": "retete de paste"})

    def test_enters_a_known_website(self) -> None:
        command = self.router.parse("Intră pe YouTube")

        self.assertEqual(command.action, Action.OPEN_URL)
        self.assertEqual(command.arguments, {"url": "https://www.youtube.com"})

    def test_opens_whatsapp(self) -> None:
        command = self.router.parse("Intră pe WhatsApp")

        self.assertEqual(command.action, Action.OPEN_WHATSAPP)

    def test_whatsapp_message_requires_confirmation(self) -> None:
        command = self.router.parse("Trimite lui mama mesajul ajung acasă în zece minute")

        self.assertEqual(command.action, Action.SEND_WHATSAPP_DRAFT)
        self.assertEqual(command.arguments, {"contact": "mama", "message": "ajung acasa in zece minute"})
        self.assertTrue(command.requires_confirmation)

    def test_starts_whatsapp_message_flow(self) -> None:
        command = self.router.parse("Trimite mesaj lui mama")

        self.assertEqual(command.action, Action.START_WHATSAPP_MESSAGE)
        self.assertEqual(command.arguments, {"contact": "mama"})

    def test_accepts_whatsapp_message_text(self) -> None:
        command = self.router.parse("Textul ajung acasă în zece minute")

        self.assertEqual(command.action, Action.SET_WHATSAPP_TEXT)
        self.assertEqual(command.arguments, {"message": "ajung acasa in zece minute"})

    def test_enters_tiktok_directly(self) -> None:
        command = self.router.parse("Intră pe TikTok")

        self.assertEqual(command.action, Action.OPEN_URL)
        self.assertEqual(command.arguments, {"url": "https://www.tiktok.com"})

    def test_enters_an_explicit_domain(self) -> None:
        command = self.router.parse("Intră pe wikipedia.org")

        self.assertEqual(command.action, Action.OPEN_URL)
        self.assertEqual(command.arguments, {"url": "https://wikipedia.org"})
