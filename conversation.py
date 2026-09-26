import os
import re

from openai import OpenAI

from config import OPENAI_MODEL, LLM_ENABLED


AUTO_MARKERS = [
    "thank you for contacting",
    "our team will get back",
    "i am an automated assistant",
    "working hours",
    "your message has been received",
    "we will respond shortly",
    "currently unavailable",
]

NEGATIVE = [
    "not interested",
    "no thanks",
    "don't need",
    "dont need",
    "stop",
    "remove me",
    "not now",
]

QUESTION_WORDS = [
    "what",
    "how",
    "when",
    "where",
    "why",
    "price",
    "cost",
    "tell me",
    "details",
]

DEFER_WORDS = [
    "later",
    "tomorrow",
    "busy",
    "not free",
    "give me time",
]

CHANGE_WORDS = [
    "change",
    "changed",
    "modify",
    "modified",
    "update",
    "updated",
    "instead",
    "make it",
    "set it",
    "switch",
    "replace",
]


def normalize(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def classify(message):

    low = normalize(message)

    if any(x in low for x in AUTO_MARKERS):
        return "auto_reply"

    if any(x in low for x in NEGATIVE):
        return "negative"

    if any(x in low for x in DEFER_WORDS):
        return "defer"

    if any(x in low for x in CHANGE_WORDS):
        return "change"

    if "?" in low or any(x in low for x in QUESTION_WORDS):
        return "question"

    return "conversation"


def llm_reply(message, last_action=None, history=None):

    api_key = os.getenv("OPENAI_API_KEY")

    if not LLM_ENABLED or not api_key:
        return None

    try:

        client = OpenAI(api_key=api_key)

        previous_action = ""

        if last_action:
            previous_action = (
                f"""
Previous ChandwaniBot action:
{last_action.get("body", "")}
"""
            )

        recent_history = ""

        if history:
            recent = history[-6:]

            recent_history = "\nRecent conversation:\n"

            for item in recent:
                role = item.get("role", "unknown")
                body = item.get("body", "")

                recent_history += (
                    f"{role}: {body}\n"
                )

        instructions = """
You are ChandwaniBot, an AI assistant helping merchants
with business growth and operational decisions.

Your job is to continue an existing merchant conversation naturally.

Rules:

1. Answer the merchant's actual question.
2. Do not invent account data, prices, offers, metrics,
   discounts, policies, or actions that were not provided.
3. Use only information available in the conversation.
4. If the merchant asks something that cannot be answered
   from the available information, say that clearly and ask
   what detail they want checked.
5. Keep replies concise and conversational.
6. Do not restart the sales pitch.
7. If the merchant agrees to something, acknowledge it and
   move the conversation forward.
8. If the merchant asks to change something, acknowledge
   the requested change.
9. Do not mention being an LLM, API, prompt, Python, or
   internal implementation.
10. Do not use markdown headings or long explanations.
11. Return only the message that should be shown to the merchant.
"""

        user_input = f"""
Merchant message:
{message}

{previous_action}

{recent_history}
"""

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            input=user_input,
        )

        text = (response.output_text or "").strip()

        if text:
            return text

    except Exception as exc:

        print(
            f"[conversation] OpenAI reply failed: {exc}"
        )

    return None


def next_reply(
    message,
    last_action=None,
    history=None
):

    intent = classify(message)


    # --------------------------------------------------------
    # AUTOMATED RESPONSE
    # --------------------------------------------------------

    if intent == "auto_reply":

        return {
            "action": "wait",
            "wait_seconds": 1800,
            "rationale": (
                "Likely automated/canned response; "
                "back off rather than consuming another "
                "conversation turn."
            ),
        }


    # --------------------------------------------------------
    # NEGATIVE / STOP
    # --------------------------------------------------------

    if intent == "negative":

        return {
            "action": "end",
            "rationale": (
                "Clear decline/stop signal; "
                "end without another promotional nudge."
            ),
        }


    # --------------------------------------------------------
    # DEFER
    # --------------------------------------------------------

    if intent == "defer":

        return {
            "action": "wait",
            "wait_seconds": 1800,
            "rationale": (
                "Merchant asked for time; "
                "respect the requested pause."
            ),
        }


    # --------------------------------------------------------
    # NORMAL CONVERSATION
    # --------------------------------------------------------

    generated = llm_reply(
        message,
        last_action=last_action,
        history=history,
    )

    if generated:

        return {
            "action": "send",
            "body": generated,
            "cta": "open_ended",
            "rationale": (
                "Generated a contextual response using "
                "the merchant's message and recent conversation."
            ),
        }


    # --------------------------------------------------------
    # FALLBACK IF OPENAI IS UNAVAILABLE
    # --------------------------------------------------------

    if intent == "question":

        return {
            "action": "send",
            "body": (
                "Sure — I can help with that. "
                "Tell me the specific detail you want me to check."
            ),
            "cta": "open_ended",
            "rationale": (
                "Question detected; OpenAI response unavailable, "
                "so a safe clarification response was used."
            ),
        }


    if intent == "change":

        return {
            "action": "send",
            "body": (
                f"Got it. I'll take the requested change into account: "
                f"\"{message.strip()}\"."
            ),
            "cta": "open_ended",
            "rationale": (
                "Change request detected; fallback response used."
            ),
        }


    return {
        "action": "send",
        "body": (
            "Got it. Tell me what you'd like to do next "
            "and I'll help from there."
        ),
        "cta": "open_ended",
        "rationale": (
            "No specific intent detected; safe conversational "
            "fallback used."
        ),
    }