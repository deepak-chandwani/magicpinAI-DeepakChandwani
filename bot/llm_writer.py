import json
import re
from config import OPENAI_API_KEY, OPENAI_MODEL, LLM_ENABLED
from policies import policy_for


class LLMWriter:
    def __init__(self):
        self.enabled = LLM_ENABLED
        self.client = None
        if self.enabled:
            from openai import OpenAI
            self.client = OpenAI(api_key=OPENAI_API_KEY)

    def rewrite(self, draft, category, merchant, trigger, customer, facts):
        if not self.enabled:
            return draft

        policy = policy_for(category)
        payload = {
            "draft": draft,
            "category": category.get("slug"),
            "policy": policy,
            "facts": facts,
            "trigger_kind": trigger.get("kind"),
            "customer_facing": bool(customer or trigger.get("scope") == "customer"),
        }
        instructions = """
You are the language layer for Vera, a merchant-growth assistant.
Rewrite the supplied draft into a concise WhatsApp message.

NON-NEGOTIABLE:
- The draft is the decision. Do not change its recommendation.
- Use ONLY facts explicitly supplied in FACTS or DRAFT.
- Never invent prices, dates, percentages, people, sources, offers, competitors, or outcomes.
- Keep exactly one primary CTA. If draft CTA is 'none', do not add one.
- Keep category vocabulary and avoid taboo terms.
- Do not add greetings or introductions that make the message longer unless useful.
- Do not mention being an AI.
- Preserve important numbers, names, dates, source citations, and offer titles exactly.
- Return JSON only: {"body":"..."}
"""
        try:
            response = self.client.responses.create(
                model=OPENAI_MODEL,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False),
            )
            raw = response.output_text.strip()
            match = re.search(r'\{.*\}', raw, flags=re.S)
            data = json.loads(match.group(0) if match else raw)
            body = str(data.get("body", "")).strip()
            if not body:
                return draft
            return body
        except Exception:
            # The deterministic draft is always the fallback. The challenge values reliability.
            return draft
