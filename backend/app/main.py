from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .errors import CrosslistError
from .models import ErrorResponse, HealthResponse, PreviewRequest, TransferPreview
from .platforms import AppleMusicClient, SpotifyClient
from .service import build_spotify_to_apple_preview
from .url_parser import spotify_playlist_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    app.state.settings = settings
    app.state.http = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="CROSSLIST API",
    version="0.1.0",
    description="Match public Spotify playlists to the Apple Music catalog.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(CrosslistError)
async def crosslist_error_handler(_: Request, exc: CrosslistError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": exc.code, "message": exc.message, "hint": exc.hint}
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "CROSSLIST", "status": "ready", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        spotify_configured=settings.spotify_configured,
        apple_music_configured=settings.apple_music_configured,
    )


@app.post(
    "/v1/transfers/spotify-to-apple/preview",
    response_model=TransferPreview,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def spotify_to_apple_preview(
    payload: PreviewRequest, request: Request
) -> TransferPreview:
    playlist_id = spotify_playlist_id(payload.playlist_url)
    settings: Settings = request.app.state.settings
    spotify = SpotifyClient(settings, request.app.state.http)
    apple_music = AppleMusicClient(settings, request.app.state.http)
    return await build_spotify_to_apple_preview(
        playlist_id=playlist_id,
        storefront=payload.storefront.lower(),
        spotify=spotify,
        apple_music=apple_music,
    )
