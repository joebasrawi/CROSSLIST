import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any


FEATURE_PATTERN = re.compile(r"\s*[\(\[]?(feat\.?|ft\.?|with)\s+.+?[\)\]]?\s*$", re.I)
EDITION_PATTERN = re.compile(
    r"(?:\s*[\(\[][^\)\]]*(?:remaster(?:ed)?|deluxe|radio edit|single version|album version|clean|explicit)[^\)\]]*[\)\]]\s*$)"
    r"|(?:\s*[-–—]\s*(?:remaster(?:ed)?|deluxe|radio edit|single version|album version|clean|explicit).*$)",
    re.I,
)
NON_WORD_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = FEATURE_PATTERN.sub("", text)
    text = EDITION_PATTERN.sub("", text)
    return NON_WORD_PATTERN.sub(" ", text.lower()).strip()


def similarity(left: str | None, right: str | None) -> float:
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def candidate_score(source: dict[str, Any], candidate: dict[str, Any]) -> float:
    attributes = candidate.get("attributes", {})
    title_score = similarity(source.get("name"), attributes.get("name"))
    artist_score = similarity(source.get("artist"), attributes.get("artistName"))
    album_score = similarity(source.get("album"), attributes.get("albumName"))

    source_duration = source.get("duration_ms")
    candidate_duration = attributes.get("durationInMillis")
    if source_duration and candidate_duration:
        delta = abs(source_duration - candidate_duration)
        duration_score = max(0.0, 1.0 - (delta / 12_000))
    else:
        duration_score = 0.5

    return round(
        (title_score * 0.42)
        + (artist_score * 0.34)
        + (album_score * 0.12)
        + (duration_score * 0.12),
        4,
    )


def best_candidate(
    source: dict[str, Any], candidates: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, float]:
    if not candidates:
        return None, 0.0
    scored = [(candidate, candidate_score(source, candidate)) for candidate in candidates]
    return max(scored, key=lambda item: item[1])
