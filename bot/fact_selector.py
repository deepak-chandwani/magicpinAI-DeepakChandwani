from datetime import datetime, date
from utils import money, pct, clean_text, best_offer, first_name, language_style


def _date_diff_days(date_str, now=None):
    try:
        d = date.fromisoformat(str(date_str)[:10])
        n = (now or datetime.now()).date()
        return (d - n).days
    except Exception:
        return None


class FactSelector:
    """Turns the large 4-context payload into a small, provenance-friendly fact packet."""

    def select(self, category, merchant, trigger, customer=None, now=None):
        kind = trigger.get("kind", "")
        p = trigger.get("payload") or {}
        identity = merchant.get("identity") or {}
        facts = []

        def add(label, value, source):
            if value not in (None, "", [], {}):
                facts.append({"label": label, "value": value, "source": source})

        add("merchant_name", identity.get("name"), "merchant.identity.name")
        add("owner_first_name", identity.get("owner_first_name") or first_name(identity.get("name")), "merchant.identity.owner_first_name")
        add("locality", identity.get("locality"), "merchant.identity.locality")
        add("city", identity.get("city"), "merchant.identity.city")
        add("category", merchant.get("category_slug") or category.get("slug"), "merchant.category_slug")

        perf = merchant.get("performance") or {}
        if perf:
            add("views_30d", perf.get("views"), "merchant.performance.views")
            add("calls_30d", perf.get("calls"), "merchant.performance.calls")
            add("directions_30d", perf.get("directions"), "merchant.performance.directions")
            add("ctr_30d", pct(perf.get("ctr"), 1), "merchant.performance.ctr")
            for k, v in (perf.get("delta_7d") or {}).items():
                add(f"delta_7d_{k}", pct(v), f"merchant.performance.delta_7d.{k}")

        # Active offer selection is a key anti-generic lever.
        offer = best_offer(merchant)
        if offer:
            add("active_offer", offer.get("title"), f"merchant.offers[{offer.get('id','?')}]")

        # Trigger-specific facts.
        if kind == "research_digest":
            top_id = p.get("top_item_id")
            item = p.get("top_item")
            if not item and top_id:
                item = next((d for d in category.get("digest", []) if d.get("id") == top_id), None)
            item = item or {}
            add("research_title", item.get("title"), f"category.digest[{item.get('id','?')}].title")
            add("research_source", item.get("source"), f"category.digest[{item.get('id','?')}].source")
            add("research_trial_n", item.get("trial_n"), f"category.digest[{item.get('id','?')}].trial_n")
            add("research_segment", item.get("patient_segment"), f"category.digest[{item.get('id','?')}].patient_segment")

        if kind in {"regulation_change", "supply_alert", "recall_due"}:
            add("source", trigger.get("source"), "trigger.source")
            for key in ("title", "circular", "batch_numbers", "manufacturer", "risk", "deadline", "deadline_iso", "action", "molecule"):
                if key in p:
                    add(key, p.get(key), f"trigger.payload.{key}")
            top_id = p.get("top_item_id")
            if top_id:
                item = next((d for d in category.get("digest", []) if d.get("id") == top_id), None)
                if item:
                    add("source_item", item.get("title"), f"category.digest[{top_id}].title")
                    add("source_citation", item.get("source"), f"category.digest[{top_id}].source")

        if kind in {"perf_dip", "seasonal_perf_dip", "perf_spike"}:
            add("performance_window_days", perf.get("window_days"), "merchant.performance.window_days")
            if p.get("metric"):
                metric = p.get("metric")
                value = perf.get(metric)
                delta = (perf.get("delta_7d") or {}).get(f"{metric}_pct")
                add("focus_metric", metric, "trigger.payload.metric")
                add("focus_metric_value", value, f"merchant.performance.{metric}")
                add("focus_metric_delta", pct(delta), f"merchant.performance.delta_7d.{metric}_pct")
            add("seasonal_context", p.get("seasonal_note"), "trigger.payload.seasonal_note")
            add("is_expected_seasonal", p.get("is_expected_seasonal"), "trigger.payload.is_expected_seasonal")

        if kind == "ipl_match_today":
            for key in ("home_team", "away_team", "venue", "start_time", "day_type", "match_date"):
                add(key, p.get(key), f"trigger.payload.{key}")
            add("peer_effect", p.get("peer_effect"), "trigger.payload.peer_effect")
            add("recommended_strategy", p.get("recommended_strategy"), "trigger.payload.recommended_strategy")

        if kind == "active_planning_intent":
            add("intent_topic", p.get("intent_topic"), "trigger.payload.intent_topic")
            add("merchant_last_message", p.get("merchant_last_message"), "trigger.payload.merchant_last_message")

        if kind == "review_theme_emerged":
            add("review_theme", p.get("theme"), "trigger.payload.theme")
            add("review_occurrences", p.get("occurrences_30d"), "trigger.payload.occurrences_30d")
            add("review_quote", p.get("common_quote"), "trigger.payload.common_quote")
            add("review_trend", p.get("trend"), "trigger.payload.trend")

        if kind == "renewal_due":
            sub = merchant.get("subscription") or {}
            add("plan", sub.get("plan"), "merchant.subscription.plan")
            add("days_remaining", sub.get("days_remaining"), "merchant.subscription.days_remaining")
            add("days_since_expiry", sub.get("days_since_expiry"), "merchant.subscription.days_since_expiry")

        if kind == "milestone_reached":
            for key in ("metric", "value", "milestone", "period"):
                add(key, p.get(key), f"trigger.payload.{key}")

        if kind == "competitor_opened":
            for key in ("competitor_name", "distance_km", "opened_date", "source"):
                add(key, p.get(key), f"trigger.payload.{key}")

        if kind == "customer_lapsed_hard" and customer:
            rel = customer.get("relationship") or {}
            add("customer_name", (customer.get("identity") or {}).get("name"), "customer.identity.name")
            add("days_since_last_visit", p.get("days_since_last_visit"), "trigger.payload.days_since_last_visit")
            add("previous_focus", p.get("previous_focus"), "trigger.payload.previous_focus")
            add("preferred_slots", (customer.get("preferences") or {}).get("preferred_slots"), "customer.preferences.preferred_slots")

        if kind in {"trial_followup", "wedding_package_followup"} and customer:
            add("customer_name", (customer.get("identity") or {}).get("name"), "customer.identity.name")
            for key in ("trial_date", "next_session_options", "wedding_date", "preferred_slot"):
                add(key, p.get(key), f"trigger.payload.{key}")
            add("language_pref", language_style(customer.get("identity") or {}), "customer.identity.language_pref")

        if kind == "chronic_refill_due" and customer:
            add("customer_name", (customer.get("identity") or {}).get("name"), "customer.identity.name")
            for key in ("medicines", "run_out_date", "total", "savings", "delivery_by", "address_saved"):
                add(key, p.get(key), f"trigger.payload.{key}")
            add("language_pref", language_style(customer.get("identity") or {}), "customer.identity.language_pref")

        if kind == "supply_alert":
            # Derived customer count: only when the trigger supplies an affected-batch mapping.
            affected = p.get("affected_customer_count")
            if affected is not None:
                add("affected_customer_count", affected, "trigger.payload.affected_customer_count")

        # Generic trigger fields are preserved so fresh, previously unseen trigger variants remain grounded.
        for key, value in p.items():
            if key in {"placeholder", "metric_or_topic", "top_item"}:
                continue
            if isinstance(value, (str, int, float, bool)):
                add(f"trigger_{key}", value, f"trigger.payload.{key}")

        return {
            "facts": facts,
            "policy": {
                "tone": (category.get("voice") or {}).get("tone"),
                "allowed_vocab": (category.get("voice") or {}).get("vocab_allowed", []),
                "taboos": (category.get("voice") or {}).get("taboos", []),
            },
            "offer_catalog": category.get("offer_catalog", []),
        }
