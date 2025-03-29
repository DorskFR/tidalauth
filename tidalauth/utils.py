import logging
import os
from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr
from tenacity import after_log, retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from tidalauth.engine import PlaywrightEngine


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given name.
    """
    return logging.getLogger(name)


class Status(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class SelectorType(StrEnum):
    CSS = "css"
    ID = "id"
    XPATH = "xpath"


def retry_with_backoff(func: Callable) -> Callable:
    """
    Decorator for retrying operations with exponential backoff
    """

    logger = get_logger(__name__)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        return func(*args, **kwargs)

    return wrapper


def get_str_value(value: Any) -> str:
    return value.get_secret_value() if isinstance(value, SecretStr) else str(value)


def report_status(func: Callable) -> Callable:
    """
    Decorator to report outcome of each function
    """

    @wraps(func)
    def wrapper(self: "PlaywrightEngine", *args: Any, **kwargs: Any) -> Any:
        # Create a readable representation of the arguments
        args_parts = [str(arg) for arg in args]
        kwargs_parts = [f"{k}={get_str_value(v)}" for k, v in kwargs.items()]
        all_args = ", ".join(args_parts + kwargs_parts)

        # Create function call description
        func_call = f"{func.__name__} ({all_args})"

        # Report that we're calling the function
        self.report(f"Calling {func_call}")

        try:
            result = func(self, *args, **kwargs)
            self.report(f"Called {func_call} successfully")
        except Exception as e:
            self.report(f"Failed to call {func_call}: {e}", status=Status.FAILED)
            raise
        else:
            return result

    return wrapper
