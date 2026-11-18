"""Ingest RBI IFSC Master dataset from Razorpay's MIT-licensed GitHub release."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/razorpay/ifsc/releases/latest"


def ingest_ifsc_master(
    base_dir: Path,
    assets_to_fetch: tuple[str, ...] = ("IFSC.csv", "banks.json"),
) -> dict[str, Any]:
    """Download latest Razorpay IFSC release assets into the immutable raw landing zone."""
    with PoliteHttpClient(timeout_s=60.0) as client:
        verdict = check_robots(GITHUB_LATEST_RELEASE_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        release_resp = client.get(GITHUB_LATEST_RELEASE_URL)
        if release_resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch GitHub release metadata: HTTP {release_resp.status_code}"
            )

        import json

        release_data = json.loads(release_resp.text)
        tag_name = release_data["tag_name"]
        published_at = release_data.get("published_at", "")

        # Save release metadata itself
        write_raw_payload(
            base_dir=base_dir,
            source="rbi_ifsc",
            filename="release_metadata.json",
            payload=release_resp.content,
            source_url=release_resp.url,
            http_status=release_resp.status_code,
            source_version=tag_name,
        )

        downloaded: dict[str, str] = {}
        for asset in release_data.get("assets", []):
            name = asset["name"]
            if name not in assets_to_fetch:
                continue
            dl_url = asset["browser_download_url"]
            asset_resp = client.get(dl_url)
            if asset_resp.status_code != 200:
                raise RuntimeError(f"Failed to download {name}: HTTP {asset_resp.status_code}")

            payload_path, _ = write_raw_payload(
                base_dir=base_dir,
                source="rbi_ifsc",
                filename=name,
                payload=asset_resp.content,
                source_url=asset_resp.url,
                http_status=asset_resp.status_code,
                source_version=tag_name,
            )
            downloaded[name] = str(payload_path)

        return {
            "source": "rbi_ifsc",
            "version": tag_name,
            "published_at": published_at,
            "robots_allowed": verdict.allowed,
            "files": downloaded,
        }


if __name__ == "__main__":
    result = ingest_ifsc_master(Path.cwd())
    print(result)
