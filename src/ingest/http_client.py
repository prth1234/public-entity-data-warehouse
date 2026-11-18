"""Polite HTTP client with exponential backoff, rate-limit handling, and honest User-Agent."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_USER_AGENT = (
    "ZintrlDataEngineeringTakeHome/1.0 "
    "(public-data-sourcing-research; respectful-crawler)"
)


@dataclass
class HttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str
    elapsed_ms: float


class PoliteHttpClient:
    """HTTP client enforcing per-host rate limits, retries, and backoff."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        backoff_base_s: float = 1.0,
        min_delay_per_host_s: float = 0.5,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self.min_delay_per_host_s = min_delay_per_host_s
        self._last_request_by_host: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_s,
            follow_redirects=True,
        )

    def _respect_rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_by_host.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < self.min_delay_per_host_s:
                time.sleep(self.min_delay_per_host_s - elapsed)
        self._last_request_by_host[host] = time.monotonic()

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Perform a GET request with retries, exponential backoff, and 429 handling."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._respect_rate_limit(url)
            start = time.monotonic()
            try:
                resp = self._client.get(url, params=params, headers=headers)
                elapsed_ms = (time.monotonic() - start) * 1000.0

                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    if attempt < self.max_retries:
                        retry_after = resp.headers.get("Retry-After")
                        wait_s = (
                            float(retry_after)
                            if retry_after and retry_after.isdigit()
                            else self.backoff_base_s * (2**attempt)
                        )
                        time.sleep(min(wait_s, 30.0))
                        continue

                return HttpResponse(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    content=resp.content,
                    text=resp.text,
                    elapsed_ms=elapsed_ms,
                )
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff_base_s * (2**attempt))
                    continue
                raise

        assert last_exc is not None
        raise last_exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
