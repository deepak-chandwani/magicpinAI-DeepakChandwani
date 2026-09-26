"""Challenge-facing deterministic compose() entry point."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))
from composer import Composer

_COMPOSER = Composer()


def compose(category: dict, merchant: dict, trigger: dict, customer: dict | None = None) -> dict:
    """Return body, CTA, send identity, suppression key and rationale."""
    return _COMPOSER.compose(category, merchant, trigger, customer)
