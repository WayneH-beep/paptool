"""Base connector definitions."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import List

from ..models import RawSignal


class BaseConnector(ABC):
    """All connectors must implement :meth:`fetch`."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def fetch(self) -> List[RawSignal]:
        """Return a list of raw signals."""

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
