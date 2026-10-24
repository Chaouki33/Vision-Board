from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_prefix="VISIONBOARD_", extra="ignore")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'visionboard.db').as_posix()}"
    secret_key: str = "dev-secret-a-changer-en-production-visionboard"
    access_token_minutes: int = 60 * 12
    cors_origins: list[str] = ["http://localhost:5173"]
    max_upload_mb: int = 20
    max_rows: int = 200_000
    # Inscription libre depuis l'écran de connexion. Le premier compte créé devient administrateur ;
    # les suivants sont des utilisateurs sans accès tant qu'ils ne créent pas de société ou que
    # l'administrateur ne leur en attribue pas. Mettre à false pour réserver la création à l'admin.
    allow_registration: bool = True

    # Rapports d'analyse rédigés par Claude. Sans clé, le SDK utilise ANTHROPIC_API_KEY
    # ou un profil `ant auth login` s'il en trouve un.
    anthropic_api_key: str | None = None
    report_model: str = "claude-opus-5-5"
    report_effort: str = "high"
    # Moteur des rapports : "auto" (Claude si une clé est configurée, sinon analyse gratuite),
    # "claude" ou "regles" (analyse automatique gratuite, sans IA ni internet).
    report_engine: str = "auto"


settings = Settings()
