from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TidalauthSettings(BaseSettings):
    """
    Settings for Tidalauth
    """

    # Base URLs
    tidalidarr_url: str = Field(default="http://127.0.0.1:8000", description="Tidalidarr instance URL")

    # Browser settings
    browser_type: str = Field(default="chromium", description="Browser to use")
    browser_version: str = Field(default="latest", description="Browser version to use")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    timeout_ms: int = Field(default=5_000, description="Default timeout for actions in milliseconds")
    sleep_ms: int = Field(default=1_000, description="Default sleep time for actions in milliseconds")
    viewport_width: int = Field(default=1920, description="Default viewport width")
    viewport_height: int = Field(default=1080, description="Default viewport height")

    # Recording settings
    take_video: bool = Field(default=False, description="Take videos for each run for debugging purposes")
    video_dir: Path = Field(default=Path("videos"), description="Directory to save videos")

    # Credentials (Without 2FA)
    user_email: str = Field(description="Account email used for device authorization")
    user_password: SecretStr = Field(description="Account password used for device authorization")

    # Sentry / Glitchtip
    sentry_dsn: str = Field(default="", description="Sentry URL to report errors")
    sentry_environment: str = Field(default="dev", description="Environment to report to Sentry")
    app_version: str = Field(default="tidalauth@latest", description="Version to report to Sentry")

    # Environment variable prefix
    model_config = SettingsConfigDict(
        env_prefix="TIDALAUTH_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
