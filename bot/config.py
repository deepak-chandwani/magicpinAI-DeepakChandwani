import os
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "2.0.0"
PORT = int(os.getenv("PORT", "8080"))
TEAM_NAME = os.getenv("TEAM_NAME", "Vera Decision Lab")
TEAM_MEMBERS = [x.strip() for x in os.getenv("TEAM_MEMBERS", "Your Name").split(",") if x.strip()]
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true" and bool(OPENAI_API_KEY)

# Keep LLM latency bounded. The challenge gives each reply 30 seconds.
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))

# Conservative defaults: Vera should not spam a merchant just because a trigger exists.
MAX_ACTIONS_PER_TICK = int(os.getenv("MAX_ACTIONS_PER_TICK", "1"))
MAX_UNANSWERED_NUDGES = int(os.getenv("MAX_UNANSWERED_NUDGES", "3"))
