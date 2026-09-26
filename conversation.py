import re
from utils import now_iso

AUTO_MARKERS = [
    "thank you for contacting",
    "our team will get back",
    "i am an automated assistant",
    "working hours",
    "your message has been received",
    "we will respond shortly",
    "currently unavailable",
]

NEGATIVE = ["not interested", "no thanks", "don't need", "dont need", "stop", "remove me", "not now"]
AFFIRMATIVE = ["yes", "okay", "ok", "send it", "do it", "interested", "sure", "join", "start", "go ahead", "let's do it", "lets do it"]
QUESTION_WORDS = ["what", "how", "when", "where", "why", "price", "cost", "tell me", "details"]


def normalize(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def classify(message):
    low = normalize(message)
    if any(x in low for x in AUTO_MARKERS):
        return "auto_reply"
    if any(x in low for x in NEGATIVE):
        return "negative"
    if any(x in low for x in AFFIRMATIVE):
        return "affirmative"
    if "?" in low or any(x in low for x in QUESTION_WORDS):
        return "question"
    if any(x in low for x in ["later", "tomorrow", "busy", "not free", "give me time"]):
        return "defer"
    return "unclear"


def next_reply(message, last_action=None):
    intent = classify(message)
    if intent == "auto_reply":
        return {"action": "wait", "wait_seconds": 1800,
                "rationale": "Likely automated/canned response; back off rather than consuming another conversation turn."}
    if intent == "negative":
        return {"action": "end",
                "rationale": "Clear decline/stop signal; end without another promotional nudge."}
    if intent == "defer":
        return {"action": "wait", "wait_seconds": 1800,
                "rationale": "Merchant asked for time; respect the requested pause."}
    if intent == "affirmative":
        return {"action": "send",
                "body": "Done — I’ll move to the next step using the details already shared. If anything changes, just tell me.",
                "cta": "open_ended",
                "rationale": "Detected affirmative intent and switched from persuasion to execution instead of re-qualifying."}
    if intent == "question":
        return {"action": "send",
                "body": "Sure — I can check that using the details already on your account. Tell me the specific point you want me to verify.",
                "cta": "open_ended",
                "rationale": "Detected information-seeking intent; continue from existing context instead of restarting the pitch."}
    return {"action": "wait", "wait_seconds": 900,
            "rationale": "No clear intent; wait rather than sending another unsolicited message."}
