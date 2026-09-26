from dataclasses import dataclass, field
from datetime import datetime, timezone
from utils import parse_dt


@dataclass
class Decision:
    send: bool
    score: float
    trigger_id: str
    kind: str
    reasons: list[str] = field(default_factory=list)
    priority: str = "normal"
    send_as: str = "vera"


BASE_SCORES = {
    "active_planning_intent": 96,
    "supply_alert": 95,
    "regulation_change": 94,
    "recall_due": 93,
    "chronic_refill_due": 92,
    "customer_lapsed_hard": 84,
    "trial_followup": 82,
    "wedding_package_followup": 82,
    "perf_dip": 76,
    "review_theme_emerged": 74,
    "seasonal_perf_dip": 73,
    "renewal_due": 72,
    "gbp_unverified": 70,
    "cde_opportunity": 70,
    "perf_spike": 68,
    "milestone_reached": 66,
    "festival_upcoming": 64,
    "ipl_match_today": 64,
    "competitor_opened": 63,
    "research_digest": 62,
    "category_seasonal": 60,
    "curious_ask_due": 58,
    "dormant_with_vera": 54,
    "winback_eligible": 52,
}


class SignalRanker:
    def rank(self, category, merchant, trigger, customer=None, now=None):
        now = now or datetime.now(timezone.utc)
        kind = trigger.get("kind", "unknown")
        payload = trigger.get("payload") or {}
        perf = merchant.get("performance") or {}
        history = merchant.get("conversation_history") or []
        signals = [str(x).lower() for x in merchant.get("signals") or []]
        score = float(BASE_SCORES.get(kind, 40))
        reasons = [f"base={BASE_SCORES.get(kind, 40)} for {kind}"]

        # Explicit merchant intent is the strongest non-safety signal.
        if kind == "active_planning_intent":
            score += 8
            reasons.append("merchant explicitly asked to plan something")

        # Hard operational/compliance triggers outrank marketing nudges.
        if kind in {"supply_alert", "regulation_change", "recall_due"}:
            score += 10
            reasons.append("time-sensitive operational/compliance event")

        # Severe performance movement is more actionable than a mild shift.
        for key in ("views_pct", "calls_pct", "ctr_pct"):
            value = (perf.get("delta_7d") or {}).get(key)
            try:
                v = abs(float(value))
                if v > 1:
                    v /= 100
                if kind in {"perf_dip", "seasonal_perf_dip"} and v >= 0.25:
                    score += 8
                    reasons.append(f"material 7d {key} movement")
            except Exception:
                pass

        # Expected seasonality should reduce panic and ad-hoc promotion.
        if kind == "seasonal_perf_dip" or payload.get("is_expected_seasonal"):
            score -= 4
            reasons.append("context marks the decline as expected seasonality")

        # Recent engagement makes another relevant follow-up more useful.
        if "engaged_in_last_48h" in signals or any(
            str(x.get("engagement", "")).lower() in {"merchant_replied", "intent_action"}
            for x in history[-3:]
        ):
            score += 5
            reasons.append("recent merchant engagement")

        # Repeated ignored outreach should lower the chance of another generic nudge.
        no_reply = sum(1 for x in history[-5:] if str(x.get("engagement", "")).lower() == "merchant_no_reply")
        if no_reply:
            score -= min(15, no_reply * 4)
            reasons.append(f"{no_reply} recent unanswered Vera touch(es)")

        # Existing offers make an action trigger easier to execute.
        if merchant.get("offers") and kind not in {"research_digest", "curious_ask_due"}:
            active = [o for o in merchant.get("offers", []) if str(o.get("status", "")).lower() in {"active", "live"}]
            if active:
                score += 3
                reasons.append("merchant has an active executable offer")

        # Customer outreach must have consent and a customer context.
        if trigger.get("scope") == "customer":
            consent = (customer or {}).get("consent") or {}
            if not consent.get("opted_in_at"):
                return Decision(False, -999, trigger.get("id", ""), kind,
                                ["customer outreach lacks explicit opt-in"], "blocked", "merchant_on_behalf")
            score += 6
            reasons.append("customer has explicit opt-in")

        # Fresh triggers are preferable to stale ones.
        expires = parse_dt(trigger.get("expires_at"))
        if expires and expires.tzinfo:
            remaining = (expires - now).total_seconds()
            if remaining <= 0:
                return Decision(False, -999, trigger.get("id", ""), kind,
                                ["trigger is expired"], "expired", "merchant_on_behalf" if customer else "vera")
            if remaining <= 24 * 3600:
                score += 5
                reasons.append("trigger expires within 24h")

        priority = "urgent" if score >= 90 else "high" if score >= 75 else "normal"
        return Decision(True, round(score, 2), trigger.get("id", ""), kind, reasons, priority,
                        "merchant_on_behalf" if customer or trigger.get("scope") == "customer" else "vera")

    def choose(self, candidates):
        """Deterministic tie-break: score, then trigger id."""
        valid = [d for d in candidates if d.send]
        if not valid:
            return None
        return sorted(valid, key=lambda d: (-d.score, d.trigger_id))[0]
