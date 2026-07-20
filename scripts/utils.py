"""
Utility and helper functions
"""

import contextlib
import logging
import os
import shutil
import warnings
from collections.abc import Iterator
from contextlib import ExitStack


def print_full_width_divider(char: str = "=") -> None:
    """
    Print a full-width divider using the specified character
    """

    print(f"{char * shutil.get_terminal_size(fallback=(80, 60)).columns}")


@contextlib.contextmanager
def _temporary_env(**env_vars: str) -> Iterator[None]:
    saved = {key: os.environ.get(key) for key in env_vars}
    os.environ.update(env_vars)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextlib.contextmanager
def _suppress_warnings() -> Iterator[None]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


@contextlib.contextmanager
def _elevate_logging_level(level: int) -> Iterator[None]:
    root_logger = logging.getLogger()
    previous_level = root_logger.level
    root_logger.setLevel(level)
    try:
        yield
    finally:
        root_logger.setLevel(previous_level)


@contextlib.contextmanager
def _suppress_ml_library_output() -> Iterator[None]:
    transformers_logging = None
    hf_progress_disabled = False

    try:
        from transformers.utils import logging as transformers_logging_module

        transformers_logging = transformers_logging_module
        transformers_logging.set_verbosity_error()
        transformers_logging.disable_progress_bar()
    except ImportError:
        pass

    try:
        from huggingface_hub.utils.tqdm import disable_progress_bars

        disable_progress_bars()
        hf_progress_disabled = True
    except ImportError:
        pass

    try:
        yield
    finally:
        if transformers_logging is not None:
            transformers_logging.enable_progress_bar()
        if hf_progress_disabled:
            try:
                from huggingface_hub.utils.tqdm import enable_progress_bars

                enable_progress_bars()
            except ImportError:
                pass


@contextlib.contextmanager
def suppress_print() -> Iterator[None]:
    with open(os.devnull, "w") as devnull, ExitStack() as stack:
        stack.enter_context(contextlib.redirect_stdout(devnull))
        stack.enter_context(contextlib.redirect_stderr(devnull))
        stack.enter_context(
            _temporary_env(
                HF_HUB_DISABLE_PROGRESS_BARS="1",
                TQDM_DISABLE="1",
                TRANSFORMERS_VERBOSITY="error",
            )
        )
        stack.enter_context(_suppress_warnings())
        stack.enter_context(_elevate_logging_level(logging.CRITICAL))
        stack.enter_context(_suppress_ml_library_output())
        yield
