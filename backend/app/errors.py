from dataclasses import dataclass


@dataclass
class CrosslistError(Exception):
    code: str
    message: str
    status_code: int = 400
    hint: str | None = None

    def __str__(self) -> str:
        return self.message
