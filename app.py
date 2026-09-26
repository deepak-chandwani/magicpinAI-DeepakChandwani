import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template_string

from config import (
    APP_VERSION,
    PORT,
    TEAM_NAME,
    TEAM_MEMBERS,
    CONTACT_EMAIL,
    OPENAI_MODEL,
    LLM_ENABLED,
    MAX_ACTIONS_PER_TICK,
)
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


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>ChandwaniBot</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Inter, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Arial, sans-serif;
            background: #f6f7f9;
            color: #182230;
        }

        /* ---------- TOP BAR ---------- */

        .topbar {
            height: 76px;
            background: #111827;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 7%;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 13px;
        }

        .logo {
            width: 42px;
            height: 42px;
            border-radius: 11px;
            background: white;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 20px;
        }

        .brand-name {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.2px;
        }

        .brand-subtitle {
            margin-top: 2px;
            color: #aeb7c6;
            font-size: 12px;
        }

        .live {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #d7dee9;
        }

        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #36c275;
        }


        /* ---------- MAIN ---------- */

        .main {
            width: 86%;
            max-width: 1250px;
            margin: 0 auto;
            padding: 48px 0 60px;
        }

        .intro {
            max-width: 780px;
            margin-bottom: 35px;
        }

        .intro-label {
            font-size: 12px;
            font-weight: 700;
            color: #667085;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            margin-bottom: 12px;
        }

        .intro h1 {
            margin: 0;
            font-size: 38px;
            line-height: 1.15;
            letter-spacing: -1px;
            font-weight: 700;
            color: #182230;
        }

        .intro p {
            margin: 15px 0 0;
            font-size: 16px;
            line-height: 1.65;
            color: #667085;
            max-width: 700px;
        }


        /* ---------- STAT CARDS ---------- */

        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }

        .stat {
            background: white;
            border: 1px solid #e4e7ec;
            border-radius: 12px;
            padding: 20px;
        }

        .stat-label {
            color: #667085;
            font-size: 12px;
            margin-bottom: 9px;
        }

        .stat-value {
            font-size: 25px;
            font-weight: 700;
            color: #182230;
        }


        /* ---------- SECTIONS ---------- */

        .section {
            margin-top: 30px;
        }

        .section-heading {
            font-size: 17px;
            font-weight: 650;
            margin-bottom: 12px;
            color: #182230;
        }

        .panel {
            background: white;
            border: 1px solid #e4e7ec;
            border-radius: 12px;
            overflow: hidden;
        }


        /* ---------- SYSTEM INFO ---------- */

        .system-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
        }

        .info-column {
            padding: 20px 24px;
        }

        .info-column + .info-column {
            border-left: 1px solid #e4e7ec;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 11px 0;
            border-bottom: 1px solid #f0f2f5;
            font-size: 13px;
        }

        .info-row:last-child {
            border-bottom: none;
        }

        .info-key {
            color: #667085;
        }

        .info-value {
            font-weight: 600;
            color: #344054;
            text-align: right;
            max-width: 60%;
        }


        /* ---------- API ---------- */

        .endpoint {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 22px;
            border-bottom: 1px solid #eef0f3;
        }

        .endpoint:last-child {
            border-bottom: none;
        }

        .endpoint-left {
            display: flex;
            align-items: center;
            gap: 13px;
        }

        .method {
            width: 48px;
            text-align: center;
            font-size: 10px;
            font-weight: 800;
            padding: 5px 6px;
            border-radius: 5px;
            background: #eef2f7;
            color: #475467;
        }

        .path {
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            color: #344054;
        }

        .endpoint-description {
            color: #98a2b3;
            font-size: 12px;
        }


        /* ---------- FOOTER ---------- */

        .footer {
            margin-top: 38px;
            padding-top: 20px;
            border-top: 1px solid #e4e7ec;
            display: flex;
            justify-content: space-between;
            color: #98a2b3;
            font-size: 12px;
        }

        .refresh {
            cursor: pointer;
            color: #667085;
        }

        .refresh:hover {
            color: #182230;
        }


        /* ---------- RESPONSIVE ---------- */

        @media (max-width: 850px) {

            .stats {
                grid-template-columns: repeat(2, 1fr);
            }

            .system-grid {
                grid-template-columns: 1fr;
            }

            .info-column + .info-column {
                border-left: none;
                border-top: 1px solid #e4e7ec;
            }

            .topbar {
                padding: 0 5%;
            }

            .main {
                width: 90%;
            }
        }

        @media (max-width: 550px) {

            .stats {
                grid-template-columns: 1fr;
            }

            .intro h1 {
                font-size: 30px;
            }

            .endpoint-description {
                display: none;
            }

            .footer {
                display: block;
            }
        }
    </style>
</head>


<body>

    <!-- TOP BAR -->

    <header class="topbar">

        <div class="brand">

            <div class="logo">C</div>

            <div>
                <div class="brand-name">ChandwaniBot</div>
                <div class="brand-subtitle">
                    AI assistant for merchant growth
                </div>
            </div>

        </div>

        <div class="live">
            <span class="live-dot"></span>
            <span id="statusText">Checking status</span>
        </div>

    </header>


    <!-- MAIN -->

    <main class="main">

        <section class="intro">

            <div class="intro-label">
                Merchant Growth Assistant
            </div>

            <h1>
                Turning merchant signals into timely actions.
            </h1>

            <p>
                ChandwaniBot monitors the context available to it,
                identifies useful business signals, and helps decide
                when a merchant should be contacted.
            </p>

        </section>


        <!-- STATS -->

        <section class="stats">

            <div class="stat">
                <div class="stat-label">Categories</div>
                <div class="stat-value" id="categories">—</div>
            </div>

            <div class="stat">
                <div class="stat-label">Merchants</div>
                <div class="stat-value" id="merchants">—</div>
            </div>

            <div class="stat">
                <div class="stat-label">Customers</div>
                <div class="stat-value" id="customers">—</div>
            </div>

            <div class="stat">
                <div class="stat-label">Triggers</div>
                <div class="stat-value" id="triggers">—</div>
            </div>

        </section>


        <!-- SYSTEM -->

        <section class="section">

            <div class="section-heading">
                System information
            </div>

            <div class="panel">

                <div class="system-grid">

                    <div class="info-column">

                        <div class="info-row">
                            <span class="info-key">Team</span>
                            <span class="info-value" id="team">—</span>
                        </div>

                        <div class="info-row">
                            <span class="info-key">Model</span>
                            <span class="info-value" id="model">—</span>
                        </div>

                        <div class="info-row">
                            <span class="info-key">Version</span>
                            <span class="info-value" id="version">—</span>
                        </div>

                    </div>


                    <div class="info-column">

                        <div class="info-row">
                            <span class="info-key">Language layer</span>
                            <span class="info-value" id="llm">—</span>
                        </div>

                        <div class="info-row">
                            <span class="info-key">Decision engine</span>
                            <span class="info-value">Signal ranking</span>
                        </div>

                        <div class="info-row">
                            <span class="info-key">Conversation handling</span>
                            <span class="info-value">Stateful</span>
                        </div>

                    </div>

                </div>

            </div>

        </section>


        <!-- API -->

        <section class="section">

            <div class="section-heading">
                API
            </div>

            <div class="panel">

                <div class="endpoint">
                    <div class="endpoint-left">
                        <span class="method">GET</span>
                        <span class="path">/v1/healthz</span>
                    </div>
                    <span class="endpoint-description">
                        Service status
                    </span>
                </div>

                <div class="endpoint">
                    <div class="endpoint-left">
                        <span class="method">GET</span>
                        <span class="path">/v1/metadata</span>
                    </div>
                    <span class="endpoint-description">
                        Bot information
                    </span>
                </div>

                <div class="endpoint">
                    <div class="endpoint-left">
                        <span class="method">POST</span>
                        <span class="path">/v1/context</span>
                    </div>
                    <span class="endpoint-description">
                        Add context
                    </span>
                </div>

                <div class="endpoint">
                    <div class="endpoint-left">
                        <span class="method">POST</span>
                        <span class="path">/v1/tick</span>
                    </div>
                    <span class="endpoint-description">
                        Generate decision
                    </span>
                </div>

                <div class="endpoint">
                    <div class="endpoint-left">
                        <span class="method">POST</span>
                        <span class="path">/v1/reply</span>
                    </div>
                    <span class="endpoint-description">
                        Continue conversation
                    </span>
                </div>

            </div>

        </section>


        <!-- FOOTER -->

        <footer class="footer">

            <span>
                ChandwaniBot · Merchant Growth Assistant
            </span>

            <span class="refresh" onclick="loadData()">
                Refresh status
            </span>

        </footer>

    </main>


    <script>

        async function loadData() {

            try {

                const healthResponse =
                    await fetch("/v1/healthz");

                const health =
                    await healthResponse.json();


                document.getElementById("statusText").textContent =
                    health.status === "ok"
                        ? "System online"
                        : "System unavailable";


                document.getElementById("categories").textContent =
                    health.contexts_loaded.category;

                document.getElementById("merchants").textContent =
                    health.contexts_loaded.merchant;

                document.getElementById("customers").textContent =
                    health.contexts_loaded.customer;

                document.getElementById("triggers").textContent =
                    health.contexts_loaded.trigger;


                document.getElementById("llm").textContent =
                    health.llm_enabled
                        ? "Enabled"
                        : "Disabled";


                const metadataResponse =
                    await fetch("/v1/metadata");

                const metadata =
                    await metadataResponse.json();


                document.getElementById("team").textContent =
                    metadata.team_name;

                document.getElementById("model").textContent =
                    metadata.model;

                document.getElementById("version").textContent =
                    metadata.version;


            } catch (error) {

                document.getElementById("statusText").textContent =
                    "Connection error";

            }

        }


        loadData();

    </script>

</body>
</html>
""")


# ============================================================
# EXISTING API
# ============================================================

def resolve_trigger(trigger_id):
    trigger = store.get("trigger", trigger_id)

    if not trigger:
        return None, None, None, None

    p = trigger.get("payload") or trigger

    merchant_id = (
        trigger.get("merchant_id")
        or p.get("merchant_id")
    )

    customer_id = (
        trigger.get("customer_id")
        or p.get("customer_id")
    )

    merchant = (
        store.get("merchant", merchant_id)
        if merchant_id else None
    )

    customer = (
        store.get("customer", customer_id)
        if customer_id else None
    )

    category_id = (
        (merchant or {}).get("category_slug")
        or p.get("category")
    )

    category = (
        store.get("category", category_id)
        if category_id else None
    )

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
        return jsonify({
            "accepted": False,
            "reason": "invalid_scope",
            "details": "scope must be category, merchant, customer, or trigger"
        }), 400

    if (
        not context_id
        or not isinstance(version, int)
        or not isinstance(payload, dict)
    ):
        return jsonify({
            "accepted": False,
            "reason": "invalid_payload"
        }), 400

    if scope == "trigger":

        payload = {
            **payload,
            "payload": {
                k: v
                for k, v in payload.items()
                if k not in {
                    "id",
                    "merchant_id",
                    "customer_id",
                    "kind",
                    "scope"
                }
            }
        }

    accepted, current = store.put(
        scope,
        context_id,
        version,
        payload
    )

    if not accepted:

        return jsonify({
            "accepted": False,
            "reason": "stale_version",
            "current_version": current
        }), 409

    return jsonify({
        "accepted": True,
        "ack_id": "ack_" + uuid.uuid4().hex[:12],
        "stored_at": now_iso()
    })


@app.get("/debug/trigger/<trigger_id>")
def debug_trigger(trigger_id):
    return jsonify(
        store.get("trigger", trigger_id) or {}
    )


@app.post("/v1/tick")
def tick():

    data = request.get_json(silent=True) or {}

    available = data.get("available_triggers") or []

    now = None

    if data.get("now"):

        try:
            now = datetime.fromisoformat(
                str(data["now"]).replace("Z", "+00:00")
            )

        except Exception:
            now = None

    decisions = []
    resolved = {}

    for tid in available:

        category, merchant, trigger, customer = \
            resolve_trigger(tid)

        if not trigger or not merchant or not category:
            continue

        if trigger.get("scope") == "customer" and not customer:
            continue

        decision = ranker.rank(
            category,
            merchant,
            trigger,
            customer,
            now=now
        )

        decisions.append(decision)

        resolved[tid] = (
            category,
            merchant,
            trigger,
            customer
        )

    selected = ranker.choose(decisions)

    actions = []

    if selected:

        category, merchant, trigger, customer = \
            resolved[selected.trigger_id]

        out = composer.compose(
            category,
            merchant,
            trigger,
            customer
        )

        suppression = out["suppression_key"]

        if store.mark_sent(suppression):

            merchant_id = merchant.get("merchant_id")

            customer_id = (
                (customer or {}).get("customer_id")
            )

            suffix = (
                customer_id
                or merchant_id
                or selected.trigger_id
            )

            conversation_id = (
                f"conv_{suffix}_{trigger.get('kind', 'event')}"
            )

            state = {
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "trigger_id": selected.trigger_id,
                "history": [{
                    "role": "vera",
                    "body": out["body"],
                    "ts": now_iso()
                }],
                "last_action": out,
                "unanswered_nudges": 0,
                "created_at": now_iso(),
            }

            store.create_conversation(
                conversation_id,
                state
            )

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

    return jsonify({
        "actions": actions
    })


@app.post("/v1/reply")
def reply():

    data = request.get_json(silent=True) or {}

    conversation_id = data.get("conversation_id")

    conv = store.get_conversation(
        conversation_id
    )

    if not conv:

        return jsonify({
            "action": "end",
            "rationale": "Unknown conversation; ending safely."
        })

    message = (
        data.get("message") or ""
    ).strip()

    conv["history"].append({
        "role": data.get("from_role", "merchant"),
        "body": message,
        "ts": now_iso()
    })

    result = next_reply(
        message,
        conv.get("last_action")
    )

    if result["action"] == "send":

        conv["history"].append({
            "role": "vera",
            "body": result["body"],
            "ts": now_iso()
        })

        conv["last_action"] = result

    return jsonify(result)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )