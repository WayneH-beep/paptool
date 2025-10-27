"""IMAP email connector to ingest newsletters or council alerts."""

from __future__ import annotations

import email
import imaplib
from typing import List

from ..config import env_or_default
from ..models import RawSignal
from .base import BaseConnector


class EmailConnector(BaseConnector):  # pragma: no cover - network interaction
    def __init__(self, host: str, username: str, password_env: str, mailbox: str = "INBOX"):
        super().__init__(name=f"email:{username}")
        self.host = host
        self.username = username
        self.password_env = password_env
        self.mailbox = mailbox

    def _fetch_messages(self) -> List[RawSignal]:
        password = env_or_default(f"env:{self.password_env}") if self.password_env else None
        if not password:
            raise RuntimeError(f"IMAP password not set in environment variable {self.password_env}")

        with imaplib.IMAP4_SSL(self.host) as client:
            client.login(self.username, password)
            client.select(self.mailbox)
            typ, data = client.search(None, "UNSEEN")
            if typ != "OK":
                return []
            signals: List[RawSignal] = []
            for num in data[0].split():
                typ, msg_data = client.fetch(num, "(RFC822)")
                if typ != "OK" or not msg_data:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                text_parts = []
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        text_parts.append(part.get_payload(decode=True).decode(part.get_content_charset("utf-8")))
                payload = {
                    "title": msg.get("Subject", ""),
                    "summary": "\n\n".join(text_parts),
                    "link": "",  # emails may not have a canonical link
                    "published": msg.get("Date", ""),
                    "author": msg.get("From", ""),
                }
                signals.append(RawSignal(source=f"email:{self.username}", payload=payload))
            return signals

    async def fetch(self) -> List[RawSignal]:
        return await self._run_in_executor(self._fetch_messages)
