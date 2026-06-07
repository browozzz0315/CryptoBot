from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from data.base import retry_on_request_error


@dataclass(slots=True)
class FearGreedClient:
    base_url: str
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry_on_request_error
    async def get_latest(self) -> dict[str, int | str | datetime]:
        response = await self._client.get(
            "/fng/",
            params={"limit": 1, "format": "json"},
        )
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("data", [])

        if not entries:
            raise ValueError("Fear & Greed API 未回傳資料")

        latest = entries[0]
        timestamp = latest.get("timestamp")
        if timestamp is None:
            raise ValueError("Fear & Greed API 回傳資料缺少 timestamp")

        return {
            "value": int(latest["value"]),
            "classification": str(latest["value_classification"]),
            "updated_at": datetime.fromtimestamp(int(timestamp), tz=UTC),
        }
