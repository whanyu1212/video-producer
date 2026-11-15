"""Minimal ElevenLabs REST client shared by the generation scripts (stdlib only).

The API key comes from ``ELEVENLABS_API_KEY`` or, failing that, a macOS Keychain
item with service ``elevenlabs-api-key``. It is never written to disk or logged.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

API_ROOT = "https://api.elevenlabs.io"
KEYCHAIN_SERVICE = "elevenlabs-api-key"


class ElevenLabsError(RuntimeError):
    """An ElevenLabs request could not be made or was rejected."""


def api_key() -> str:
    """Return the API key from the environment or the macOS Keychain.

    Raises:
        ElevenLabsError: If neither source has a key.
    """
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        return key
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        raise ElevenLabsError(
            "No ElevenLabs API key: set ELEVENLABS_API_KEY or add a Keychain item "
            f"with service '{KEYCHAIN_SERVICE}'"
        ) from err
    return result.stdout.strip()


def post(
    path: str,
    *,
    body: bytes,
    content_type: str,
    query: dict[str, str] | None = None,
    timeout: float = 300,
) -> bytes:
    """POST to the API and return the raw response body.

    Raises:
        ElevenLabsError: On an HTTP error status or a network failure.
    """
    url = API_ROOT + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"xi-api-key": api_key(), "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")[:2000]
        raise ElevenLabsError(f"POST {path} failed with HTTP {err.code}: {detail}") from err
    except urllib.error.URLError as err:
        raise ElevenLabsError(f"POST {path} failed: {err.reason}") from err


def post_json(
    path: str, payload: dict[str, object], *, query: dict[str, str] | None = None, timeout: float = 300
) -> bytes:
    return post(
        path,
        body=json.dumps(payload).encode(),
        content_type="application/json",
        query=query,
        timeout=timeout,
    )


def post_multipart(
    path: str, fields: dict[str, str], *, file_field: str, file_path: Path, timeout: float = 600
) -> bytes:
    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    ]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{file_path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
    )
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return post(
        path,
        body=b"".join(parts),
        content_type=f"multipart/form-data; boundary={boundary}",
        timeout=timeout,
    )


def next_take(directory: Path, stem: str, suffix: str) -> Path:
    """Return the first unused ``<stem>_v<N><suffix>`` path, so takes are never overwritten."""
    directory.mkdir(parents=True, exist_ok=True)
    take = 1
    while (directory / f"{stem}_v{take}{suffix}").exists():
        take += 1
    return directory / f"{stem}_v{take}{suffix}"


def write_sidecar(
    media: Path, *, tool: str, request: dict[str, object], credits_estimate: float | None
) -> Path:
    """Record how a generated file was made next to it (``<file>.gen.json``)."""
    sidecar = media.with_suffix(".gen.json")
    record = {
        "tool": tool,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "file": media.name,
        "credits_estimate": credits_estimate,
        "request": request,
    }
    sidecar.write_text(json.dumps(record, indent=2) + "\n")
    return sidecar
