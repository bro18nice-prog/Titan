"""Teste pentru API-ul privat al aplicației TITAN Mobile."""

import unittest

from fastapi.testclient import TestClient

from titan.mobile.server import create_app


class RecordingAssistant:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def handle(self, text: str) -> str:
        self.commands.append(text)
        return f"Execut local: {text}"


class MobileServerTests(unittest.TestCase):
    def test_command_gets_a_session_and_keeps_it(self) -> None:
        client = TestClient(create_app(assistant_factory=RecordingAssistant, access_token="test-token"))
        headers = {"Authorization": "Bearer test-token"}
        first = client.post("/api/commands", json={"text": "aprinde becul"}, headers=headers)
        self.assertEqual(first.status_code, 200)
        session_id = first.json()["session_id"]

        second = client.post(
            "/api/commands",
            json={"text": "stinge becul", "session_id": session_id},
            headers=headers,
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["session_id"], session_id)
        self.assertIn("stinge becul", second.json()["response"])

    def test_protected_api_rejects_missing_token(self) -> None:
        client = TestClient(create_app(assistant_factory=RecordingAssistant, access_token="test-token"))
        response = client.get("/api/status")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
