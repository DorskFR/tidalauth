import requests
import sentry_sdk

from tidalauth.engine import PlaywrightEngine
from tidalauth.settings import TidalauthSettings
from tidalauth.utils import USER_AGENT, get_logger


def main() -> None:
    settings = TidalauthSettings()
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=settings.app_version,
        environment=settings.sentry_environment,
        sample_rate=1.0,
        enable_tracing=True,
        traces_sample_rate=1.0,
    )
    logger = get_logger(__name__)
    engine = PlaywrightEngine(settings)
    engine.setup()

    # Main loop

    # Call Tidalidarr's /auth
    base_url = f"{settings.tidalidarr_url}".removesuffix("/")
    response = requests.get(f"{base_url}/auth", headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    content = response.text

    if "https://link.tidal.com" not in content:
        logger.info("Authorization does not seem required")
        return

    authorization_url = content.strip()
    logger.info(f"Authorization is required, URL: {authorization_url}")

    engine.navigate(authorization_url)


if __name__ == "__main__":
    main()
