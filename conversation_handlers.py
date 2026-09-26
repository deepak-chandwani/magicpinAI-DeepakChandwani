"""Optional multi-turn handler required by the challenge brief."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))
from conversation import next_reply


def respond(state: dict, merchant_message: str) -> dict:
    return next_reply(merchant_message, state.get("last_action"))
