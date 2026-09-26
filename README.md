# Vera AI Challenge — Decision-First Bot

## Core idea

Most LLM submissions start with `context -> LLM -> message`. This bot deliberately does not.

It uses:

1. **Signal ranking** — decide whether Vera should speak and which active trigger deserves attention.
2. **Fact selection** — reduce the full context to a small set of verifiable facts with provenance.
3. **Category policy** — enforce domain vocabulary and taboos outside the model.
4. **Deterministic templates** — guarantee a safe fallback even when the LLM is unavailable.
5. **Optional OpenAI language layer** — rewrite only the already-decided draft; it may not invent facts or change the decision.
6. **Conversation state machine** — recognize auto-replies, declines, deferrals, questions and affirmative intent.
7. **Suppression** — avoid duplicate outreach and excessive nudging.

## Why this should score well

The judge rewards decision quality, specificity, category fit, merchant fit and engagement. The design therefore optimizes for:

- one strongest signal rather than every signal
- concrete numbers, dates, offers and source citations
- existing merchant offers before invented campaigns
- category-specific vocabulary
- customer consent
- knowing when **not** to send
- intent handoff after a merchant says yes
- anti-repetition and auto-reply handling

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m pytest -q
python app.py
```

Health check: `http://localhost:8080/v1/healthz`

## Enable OpenAI

Copy `.env.example` to `.env` and set:

```text
LLM_ENABLED=true
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5.6-luna
```

Never commit `.env` or an API key.

## Judge

From the challenge root, configure the official `judge_simulator.py` with your bot URL and judge LLM credentials, then run:

```bash
python judge_simulator.py
```

Use the score breakdown to improve the **rules**, not to hardcode the 30 known cases.

## Deployment

Render is supported by the included `render.yaml`. The public URL must remain live during evaluation.
