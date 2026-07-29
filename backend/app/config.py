from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    spotify_client_id: str | None
    spotify_client_secret: str | None
    apple_music_developer_token: str | None
    request_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            apple_music_developer_token=os.getenv("APPLE_MUSIC_DEVELOPER_TOKEN"),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        )

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def apple_music_configured(self) -> bool:
        return bool(self.apple_music_developer_token)

