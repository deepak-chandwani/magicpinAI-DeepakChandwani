# Build Vera step-by-step

## 1. Install Python
Use Python 3.12 for the cleanest deployment path.

## 2. Create environment

### Windows PowerShell
```powershell
cd magicpin_vera_submission\bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux
```bash
cd magicpin_vera_submission/bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Run deterministic mode first

Keep `LLM_ENABLED=false`.

```bash
python -m pytest -q test_engine.py test_local.py
python app.py
```

Open:
`http://localhost:8080/v1/healthz`

## 4. Understand the pipeline

`POST /v1/context` -> `store.py`

`POST /v1/tick` -> `ranker.py` -> `fact_selector.py` -> `composer.py` -> optional `llm_writer.py`

`POST /v1/reply` -> `conversation.py`

## 5. Use OpenAI safely

OpenAI is a language layer, not the decision maker.

1. Copy `.env.example` to `.env`.
2. Set `LLM_ENABLED=true` and `OPENAI_API_KEY`.
3. Start locally.
4. Compare LLM-polished output against deterministic output.
5. For final competition submission, prefer the deterministic output if the LLM introduces instability or unsupported facts.

## 6. Regenerate the 30-line submission

From the challenge root:

```bash
python make_submission.py
python quality_audit.py
```

## 7. Run the official judge

Use the supplied `judge_simulator.py`. Point `BOT_URL` at your local or deployed service and configure its own judge LLM key.

Do not optimize by copying case-study wording. Optimize the decision rules that produced the case-study shape.

## 8. Deployment

Push the project to GitHub and deploy the included `render.yaml` on Render. Add the secret `OPENAI_API_KEY` only in Render's environment variables if you keep runtime LLM enabled.
