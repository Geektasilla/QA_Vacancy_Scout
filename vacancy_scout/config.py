"""Runtime configuration. All credentials come from environment variables only."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Job boards to monitor: human-readable name -> search results URL.
JOB_TARGETS: dict[str, str] = {
    "Stepstone · QA Automation": "https://www.stepstone.de/jobs/qa-automation",
    "Stepstone · Manual QA": "https://www.stepstone.de/jobs/manual-qa",
}

READER_PROXY = "https://r.jina.ai/"  # turns any web page into LLM-friendly plain text
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_STATE_FILE = "state/seen_vacancies.json"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    telegram_token: str = field(repr=False)
    telegram_chat_id: str = field(repr=False)
    model: str = DEFAULT_MODEL
    state_file: str = DEFAULT_STATE_FILE
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        dry_run = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes"}

        required = ["OPENAI_API_KEY"] if dry_run else ["OPENAI_API_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ConfigError(f"Missing environment variables: {', '.join(missing)}")

        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            state_file=os.getenv("STATE_FILE", DEFAULT_STATE_FILE),
            dry_run=dry_run,
        )

    def __repr__(self) -> str:  # never print secrets in logs
        return f"Settings(model={self.model!r}, state_file={self.state_file!r}, dry_run={self.dry_run})"
