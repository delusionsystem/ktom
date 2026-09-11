from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | Path | None = None) -> None:
    env_path = Path(path) if path else Path(__file__).resolve().parents[1] / '.env'
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


@dataclass(frozen=True)
class Settings:
    host: str = '0.0.0.0'
    port: int = 8080
    discogs_token: str | None = None
    kiosk_browser: bool = True

    @classmethod
    def from_environment(cls) -> 'Settings':
        load_dotenv()
        port_value = os.getenv('KTOM_PORT', str(cls.port))
        try:
            port = int(port_value)
        except ValueError as error:
            raise ValueError('KTOM_PORT must be an integer') from error
        if not 1 <= port <= 65535:
            raise ValueError('KTOM_PORT must be between 1 and 65535')
        kiosk_value = os.getenv('KTOM_KIOSK_BROWSER', 'true').strip().lower()
        return cls(
            host=os.getenv('KTOM_HOST', cls.host),
            port=port,
            discogs_token=os.getenv('DISCOGS_TOKEN') or None,
            kiosk_browser=kiosk_value not in {'0', 'false', 'no', 'off'},
        )
