import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify

from config import APP_VERSION, PORT, TEAM_NAME, TEAM_MEMBERS, CONTACT_EMAIL, OPENAI_MODEL, LLM_ENABLED, MAX_ACTIONS_PER_TICK
from store import ContextStore
from composer import Composer
from ranker import SignalRanker
from conversation import next_reply
from utils import now_iso

app = Flask(__name__)
started = time.time()
store = ContextStore()
composer = Composer()
ranker = SignalRanker()

VALID_SCOPES = {"category", "merchant", "customer", "trigger"}


def resolve_trigger(trigger_id):
    trigger = store.get("trigger", trigger_id)
    if not trigger:
        return None, None, None, None
    p = trigger.get("payload") or trigger
    merchant_id = trigger.get("merchant_id") or p.get("merchant_id")
    customer_id = trigger.get("customer_id") or p.get("customer_id")
    merchant = store.get("merchant", merchant_id) if merchant_id else None
    customer = store.get("customer", customer_id) if customer_id else None
    category_id = (merchant or {}).get("category_slug") or p.get("category")
    category = store.get("category", category_id) if category_id else None
    return category, merchant, trigger, customer


@app.get("/v1/healthz")
def healthz():
    return jsonify({
        "status": "ok",
        "uptime_seconds": round(time.time() - started, 2),
        "contexts_loaded": store.counts(),
        "llm_enabled": LLM_ENABLED,
    })


@app.get("/v1/metadata")
def metadata():
    return jsonify({
        "team_name": TEAM_NAME,
        "team_members": TEAM_MEMBERS,
        "model": OPENAI_MODEL if LLM_ENABLED else "deterministic-v2",
        "approach": "deterministic signal ranking + provenance-aware fact selection + category policy + optional OpenAI language layer + stateful reply handling",
        "contact_email": CONTACT_EMAIL,
        "version": APP_VERSION,
        "submitted_at": os.getenv("SUBMITTED_AT", now_iso()),
    })


@app.post("/v1/context")
def context():
    data = request.get_json(silent=True) or {}
    scope = data.get("scope")
    context_id = data.get("context_id")
    version = data.get("version")
    payload = data.get("payload")

    if scope not in VALID_SCOPES:
        return jsonify({"accepted": False, "reason": "invalid_scope", "details": "scope must be category, merchant, customer, or trigger"}), 400
    if not context_id or not isinstance(version, int) or not isinstance(payload, dict):
        return jsonify({"accepted": False, "reason": "invalid_payload"}), 400

    if scope == "trigger":
        payload = {
            **payload,
            "payload": {
                k: v for k, v in payload.items()
                if k not in {"id", "merchant_id", "customer_id", "kind", "scope"}
        }
    }
    accepted, current = store.put(scope, context_id, version, payload)
    if not accepted:
        return jsonify({"accepted": False, "reason": "stale_version", "current_version": current}), 409
    return jsonify({"accepted": True, "ack_id": "ack_" + uuid.uuid4().hex[:12], "stored_at": now_iso()})

@app.get("/debug/trigger/<trigger_id>")
def debug_trigger(trigger_id):
    return jsonify(store.get("trigger", trigger_id) or {})
@app.post("/v1/tick")
def tick():
    data = request.get_json(silent=True) or {}
    available = data.get("available_triggers") or []
    now = None
    if data.get("now"):
        try:
            now = datetime.fromisoformat(str(data["now"]).replace("Z", "+00:00"))
        except Exception:
            now = None

    decisions = []
    resolved = {}
    for tid in available:
        category, merchant, trigger, customer = resolve_trigger(tid)
        if not trigger or not merchant or not category:
            continue
        if trigger.get("scope") == "customer" and not customer:
            continue
        decision = ranker.rank(category, merchant, trigger, customer, now=now)
        decisions.append(decision)
        resolved[tid] = (category, merchant, trigger, customer)

    selected = ranker.choose(decisions)
    actions = []
    if selected:
        category, merchant, trigger, customer = resolved[selected.trigger_id]
        out = composer.compose(category, merchant, trigger, customer)
        suppression = out["suppression_key"]
        if store.mark_sent(suppression):
            merchant_id = merchant.get("merchant_id")
            customer_id = (customer or {}).get("customer_id")
            # Meaningful conversation id makes replay/debugging easier.
            suffix = customer_id or merchant_id or selected.trigger_id
            conversation_id = f"conv_{suffix}_{trigger.get('kind','event')}"
            state = {
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "trigger_id": selected.trigger_id,
                "history": [{"role": "vera", "body": out["body"], "ts": now_iso()}],
                "last_action": out,
                "unanswered_nudges": 0,
                "created_at": now_iso(),
            }
            store.create_conversation(conversation_id, state)
            actions.append({
                "conversation_id": conversation_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "send_as": out["send_as"],
                "trigger_id": selected.trigger_id,
                "template_name": out.get("template_name"),
                "template_params": out.get("template_params", []),
                "body": out["body"],
                "cta": out["cta"],
                "suppression_key": suppression,
                "rationale": out["rationale"],
            })

    return jsonify({"actions": actions})


@app.post("/v1/reply")
def reply():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    conv = store.get_conversation(conversation_id)
    if not conv:
        return jsonify({"action": "end", "rationale": "Unknown conversation; ending safely."})

    message = (data.get("message") or "").strip()
    conv["history"].append({"role": data.get("from_role", "merchant"), "body": message, "ts": now_iso()})
    result = next_reply(message, conv.get("last_action"))
    if result["action"] == "send":
        conv["history"].append({"role": "vera", "body": result["body"], "ts": now_iso()})
        conv["last_action"] = result
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
