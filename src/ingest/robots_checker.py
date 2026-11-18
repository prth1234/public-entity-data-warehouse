"""robots.txt compliance checker that runs before any HTTP fetch."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from src.ingest.http_client import DEFAULT_USER_AGENT, PoliteHttpClient


@dataclass
class RobotsVerdict:
    url: str
    robots_url: str
    allowed: bool
    status_code: int | None
    reason: str


def check_robots(
    url: str,
    client: PoliteHttpClient | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> RobotsVerdict:
    """Fetch and evaluate robots.txt for the target URL before any ingestion."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    owns_client = client is None
    if client is None:
        client = PoliteHttpClient(user_agent=user_agent)

    try:
        resp = client.get(robots_url)
        if resp.status_code == 404:
            return RobotsVerdict(
                url=url,
                robots_url=robots_url,
                allowed=True,
                status_code=404,
                reason="robots.txt returned 404 (no restrictions published)",
            )
        if resp.status_code >= 400:
            return RobotsVerdict(
                url=url,
                robots_url=robots_url,
                allowed=False,
                status_code=resp.status_code,
                reason=f"robots.txt returned HTTP {resp.status_code}; failing closed",
            )

        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())
        allowed = rp.can_fetch(user_agent, url)
        return RobotsVerdict(
            url=url,
            robots_url=robots_url,
            allowed=allowed,
            status_code=resp.status_code,
            reason="Allowed by robots.txt" if allowed else "Disallowed by robots.txt",
        )
    except Exception as exc:
        return RobotsVerdict(
            url=url,
            robots_url=robots_url,
            allowed=False,
            status_code=None,
            reason=f"robots.txt fetch error ({exc}); failing closed",
        )
    finally:
        if owns_client:
            client.close()
