# magicpin Vera AI Challenge — Start Here

You already know Python + Flask, so the fastest route is:

1. Open the `bot/` folder.
2. Create a virtual environment and install `requirements.txt`.
3. Run `python app.py`.
4. Test `GET /v1/healthz` and `GET /v1/metadata`.
5. Use the included expanded dataset to replay contexts.
6. Run the official `judge_simulator.py` after putting your OpenAI API key into its configuration.
7. Iterate based on the judge's five scores.

## Architecture

`POST /v1/context` → versioned in-memory context store

`POST /v1/tick` → trigger selection → deterministic composer → suppression

`POST /v1/reply` → intent / auto-reply / decline handling

The composer is intentionally deterministic. The OpenAI key is not embedded in the code and should never be committed to GitHub.

## Where to focus for score

- Decision quality: prioritize explicit/actionable triggers over generic signals.
- Specificity: always quote a real number/date/offer/source when present.
- Category fit: use category vocabulary and avoid category taboos.
- Merchant fit: use the merchant's actual metric, offer, locality, or history.
- Engagement: one reason + one low-effort CTA.

## OpenAI

Use your API key as an environment variable if we add an LLM polishing layer later. Do not paste the key into source code or into the submission README.
