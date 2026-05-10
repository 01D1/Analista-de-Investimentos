from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent.parent

REQUIRED_IN_PRODUCTION = ["anthropic_api_key", "telegram_bot_token", "telegram_chat_id"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[ROOT / ".env", ROOT / "env"],  # aceita .env ou env (sem ponto)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,  # variáveis vazias no OS não sobrescrevem o arquivo env
    )

    # --- Ambiente ---
    env: Literal["development", "production"] = "development"

    # --- Paths ---
    data_raw: Path = ROOT / "data" / "raw"
    data_processed: Path = ROOT / "data" / "processed"
    data_output: Path = ROOT / "data" / "output"
    logs_dir: Path = ROOT / "logs"

    # --- Obsidian vault ---
    vault_path: Path = ROOT.parent  # um nível acima de 12_PYTHON/ → raiz do vault Obsidian

    # --- APIs externas ---
    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Claude ---
    claude_model_content: str = "claude-sonnet-4-6"
    claude_model_classify: str = "claude-haiku-4-5-20251001"

    # --- CVM ---
    cvm_base_url: str = "https://dados.cvm.gov.br/dados"
    cvm_timeout: int = 60
    cvm_retry_attempts: int = 3

    def model_post_init(self, __context) -> None:
        for path in (self.data_raw, self.data_processed, self.data_output, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)

        # Startup validation: fail loudly in production if required keys are missing (D-FOUND-02)
        if self.env == "production":
            missing = [k for k in REQUIRED_IN_PRODUCTION if not getattr(self, k, "")]
            if missing:
                import sys
                print(f"[CONFIG] Variáveis obrigatórias ausentes no .env: {missing}")
                sys.exit(1)

    @property
    def tickers(self) -> list[dict]:
        path = ROOT / "config" / "tickers.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return data.get("tickers", [])

    @property
    def active_tickers(self) -> list[str]:
        return [t["ticker"] for t in self.tickers if t.get("active", True)]


settings = Settings()
