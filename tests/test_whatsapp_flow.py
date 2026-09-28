import unittest

from titan.core.assistant import TitanAssistant


class FakeWindows:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.send_called = False

    def open_url(self, url: str) -> str:
        self.urls.append(url)
        return "Deschid pagina cerută."

    def send_whatsapp_message(self) -> str:
        self.send_called = True
        return "Am trimis mesajul WhatsApp confirmat."


class FakeContacts:
    def phone_for(self, alias: str) -> str | None:
        return "40746658434" if alias == "soltuzu" else None

    def draft_url(self, alias: str, message: str) -> str | None:
        if self.phone_for(alias):
            return f"https://web.whatsapp.com/send?phone=40746658434&text={message}"
        return None


class WhatsAppFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assistant = TitanAssistant()
        self.assistant.windows = FakeWindows()
        self.assistant.whatsapp = FakeContacts()

    def test_message_requires_recipient_text_confirmation_then_send(self) -> None:
        response = self.assistant.handle("trimite mesaj lui soltuzu")
        self.assertIn("Care este textul", response)

        response = self.assistant.handle("textul salut")
        self.assertIn("Confirmi mesajul către soltuzu", response)

        response = self.assistant.handle("da")
        self.assertIn("spune «trimite»", response)
        self.assertEqual(len(self.assistant.windows.urls), 1)

        response = self.assistant.handle("trimite")
        self.assertEqual(response, "Am trimis mesajul WhatsApp confirmat.")
        self.assertTrue(self.assistant.windows.send_called)

    def test_unknown_contact_does_not_start_message(self) -> None:
        response = self.assistant.handle("trimite mesaj lui necunoscut")

        self.assertIn("Nu găsesc contactul", response)

