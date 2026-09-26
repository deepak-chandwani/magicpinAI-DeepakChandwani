import re
from policies import policy_for
from utils import first_name, best_offer, pct, money, language_style
from fact_selector import FactSelector
from llm_writer import LLMWriter


class Composer:
    def __init__(self):
        self.fact_selector = FactSelector()
        self.writer = LLMWriter()

    def base(self, body, cta, send_as, trigger, rationale, params=None, template_name=None):
        return {
            "body": body.strip(),
            "cta": cta,
            "send_as": send_as,
            "suppression_key": trigger.get("suppression_key") or trigger.get("id"),
            "rationale": rationale,
            "template_name": template_name or f"vera_{trigger.get('kind','generic')}_v2",
            "template_params": params or [],
        }

    def compose(self, category, merchant, trigger, customer=None):
        packet = self.fact_selector.select(category, merchant, trigger, customer)
        draft = self._draft(category, merchant, trigger, customer, packet)

# Keep metric-driven performance messages deterministic.
# The LLM must not alter factual metrics or percentages.
        if trigger.get("kind") not in {"perf_dip", "perf_spike", "seasonal_perf_dip"}:
            draft["body"] = self.writer.rewrite(
            draft["body"],
            category,
            merchant,
            trigger,
            customer,
            packet["facts"],
        )

        draft["body"] = self._guardrail(draft["body"], category, packet)
        return draft

    def _draft(self, c, m, t, customer, packet):
        kind = t.get("kind", "")
        if customer or t.get("scope") == "customer":
            return self._customer(c, m, t, customer, packet)
        return self._merchant(c, m, t, packet)

    def _merchant(self, c, m, t, packet):
        name = (m.get("identity") or {}).get("owner_first_name") or first_name((m.get("identity") or {}).get("name"))
        locality = (m.get("identity") or {}).get("locality")
        p = t.get("payload") or {}
        kind = t.get("kind", "")
        offer = best_offer(m)
        offer_text = offer.get("title") if offer else None
        peer = c.get("peer_stats") or {}
        policy = policy_for(c)

        if kind == "research_digest":
            facts = packet["facts"]
            title = next((x["value"] for x in facts if x["label"] == "research_title"), None)
            source = next((x["value"] for x in facts if x["label"] == "research_source"), None)
            trial = next((x["value"] for x in facts if x["label"] == "research_trial_n"), None)
            segment = next((x["value"] for x in facts if x["label"] == "research_segment"), None)
            body = f"{name}, one relevant {c.get('slug','business')} update: {title or 'a new digest item'}"
            if trial: body += f" — {int(trial):,}-participant"
            if segment: body += f" study for {str(segment).replace('_',' ')}"
            if source: body += f". Source: {source}"
            body += ". Want me to turn it into one ready-to-review customer post?"
            return self.base(body, "open_ended", "vera", t,
                             "Research trigger selected because it is fresh and category-relevant; source and study facts are grounded in the category digest.", [title, source])

        if kind == "regulation_change":
            title = p.get("title") or p.get("circular") or "a regulatory update"
            source = p.get("source") or t.get("source")
            deadline = p.get("deadline_iso") or p.get("deadline")
            body = f"{name}, heads-up: {title}"
            if source: body += f" ({source})"
            if deadline: body += f". Deadline: {deadline}"
            body += ". Want me to turn the documented requirements into a short action checklist?"
            return self.base(body, "open_ended", "vera", t,
                             "Compliance trigger outranks promotional signals; message points to documented source and converts it into an actionable checklist.", [title, source, deadline])

        if kind in {"supply_alert", "recall_due"}:
            title = p.get("title") or "urgent supply/recall alert"
            batches = p.get("batch_numbers") or p.get("batches")
            manufacturer = p.get("manufacturer")
            risk = p.get("risk")
            affected = p.get("affected_customer_count")
            body = f"{name}, urgent: {title}"
            if batches: body += f" — batches {', '.join(batches) if isinstance(batches, list) else batches}"
            if manufacturer: body += f" by {manufacturer}"
            if risk: body += f"; {risk}"
            if affected is not None: body += f". I found {affected} potentially affected customer record(s) in the supplied data"
            body += ". Want me to draft the customer notice and replacement workflow?"
            return self.base(body, "open_ended", "vera", t,
                             "Time-sensitive supply/compliance signal selected; uses only supplied batch/manufacturer/risk facts and offers one executable next step.", [title, batches, manufacturer])

        if kind == "ipl_match_today":
            teams = " vs ".join([x for x in [p.get("home_team"), p.get("away_team")] if x])
            when = p.get("start_time")
            day_type = p.get("day_type")
            peer_effect = p.get("peer_effect")
            recommendation = p.get("recommended_strategy")
            body = f"Quick heads-up {name} — {teams or 'IPL match'}"
            if when: body += f" at {when}"
            if p.get("venue"): body += f" at {p['venue']}"
            if peer_effect: body += f". Your supplied local signal says {peer_effect}"
            if day_type: body += f" on {day_type}"
            if recommendation: body += f". Recommendation: {recommendation}"
            elif offer_text: body += f". I'd use your existing {offer_text} rather than inventing a new offer"
            body += ". Want me to draft the single best delivery/listing message?"
            return self.base(body, "open_ended", "vera", t,
                             "Event trigger is interpreted through the supplied peer effect/recommendation rather than blindly promoting the event.", [teams, when, peer_effect, recommendation])

        if kind == "active_planning_intent":
            topic = p.get("intent_topic") or "the idea you raised"
            last = p.get("merchant_last_message")
            body = f"{name}, I can turn your {str(topic).replace('_',' ')} idea into a first draft"
            if last: body += ". I have your latest planning note in context"
            body += ". Want me to draft the version you can review?"
            return self.base(body, "open_ended", "vera", t,
                             "Explicit merchant planning intent is the highest-value signal; move directly into artifact creation instead of re-pitching.", [topic])

        if kind == "review_theme_emerged":
            theme = p.get("theme") or "a recurring review theme"
            n = p.get("occurrences_30d")
            quote = p.get("common_quote")
            trend = p.get("trend")
            body = f"{name}, {n or 'several'} recent reviews mention {str(theme).replace('_',' ')}"
            if trend: body += f", and the theme is {trend}"
            if quote: body += f". One example: \"{quote}\""
            body += ". Want me to draft the listing/reply fix around this theme?"
            return self.base(body, "open_ended", "vera", t,
                             "Review theme is a merchant-specific signal with concrete evidence; turn it into one practical listing/reply action.", [theme, n, quote])

        if kind in {"perf_dip", "perf_spike", "seasonal_perf_dip"}:
            metric = p.get("metric") or "views"
            delta = (m.get("performance") or {}).get("delta_7d", {}).get(f"{metric}_pct")
            delta_text = pct(delta) or "a recent shift"
            expected = p.get("is_expected_seasonal")
            if kind == "seasonal_perf_dip" or expected:
                body = f"{name}, {metric} are down {delta_text} this week, but your trigger marks this as expected seasonality. I’d avoid reacting with extra spend; want me to draft a retention-focused action for the current window?"
                rationale = "Seasonal dip is explicitly marked expected; reframe rather than treating normal seasonality as a crisis."
            elif kind == "perf_spike":
                if delta is not None and delta < 0:
                    body = f"{name}, {metric} are down {pct(abs(delta))} over the last 7 days. The current signal is weaker than expected. Want me to draft one recovery action?"
                    rationale = "The supplied performance metric is negative, so the message follows the measured direction rather than the trigger label."
                else:
                    body = f"{name}, {metric} are up {delta_text} over the last 7 days. That is a useful moment to capture what is working before it fades. Want me to draft one action around the strongest current signal?"
                    rationale = "Positive performance spike creates a timely opportunity to preserve a winning signal."
            else:
                body = f"{name}, {metric} are down {delta_text} over the last 7 days. I found this as the current performance signal"
    
                if offer_text:
                    body += f"; want me to draft one recovery action using your existing {offer_text}?"
                    rationale = "Performance dip is actionable and is paired with the merchant's actual metric movement and active offer."
                else:
                    body += "; want me to draft one recovery action based on this signal?"
                    rationale = "Performance dip is actionable and is paired with the merchant's actual metric movement; no active offer was assumed."
            return self.base(body, "open_ended", "vera", t, rationale, [metric, delta_text, offer_text])

        if kind == "renewal_due":
            sub = m.get("subscription") or {}
            days = sub.get("days_remaining")
            body = f"{name}, your {sub.get('plan','subscription')} plan has {days} day(s) remaining. Want me to prepare the renewal details so you can review them?"
            return self.base(body, "open_ended", "vera", t, "Subscription deadline is explicit and operational; ask for one review action without inventing pricing.")

        if kind == "gbp_unverified":
            body = f"{name}, your business listing is still unverified in the supplied account data. That can limit profile control. Want me to give you the shortest verification checklist?"
            return self.base(body, "open_ended", "vera", t, "Listing verification is an actionable account-state issue, not a generic campaign suggestion.")

        if kind == "curious_ask_due":
            body = f"Hi {name}! Quick question: what service has been asked for most this week at {m.get('identity',{}).get('name','your business')}? I’ll turn your answer into one ready-to-use customer reply."
            return self.base(body, "open_ended", "vera", t, "Curious-ask trigger is intentionally a low-effort question with immediate reciprocity.")

        if kind == "milestone_reached":
            metric = p.get("metric") or "metric"
            value = p.get("value") or p.get("milestone")
            body = f"{name}, you just reached {value} on {metric}. Want me to turn the milestone into one customer-facing post?"
            return self.base(body, "open_ended", "vera", t, "Milestone is used as a timely proof point and converted into one reusable asset.")

        if kind == "competitor_opened":
            comp = p.get("competitor_name")
            dist = p.get("distance_km")
            body = f"{name}, a new nearby competitor is in the supplied local signal"
            if comp: body += f": {comp}"
            if dist: body += f" ({dist} km)"
            body += ". Rather than copying them, want me to identify one defensible listing advantage from your existing data?"
            return self.base(body, "open_ended", "vera", t, "Competitive signal is converted into differentiation work rather than an unsupported competitive claim.")

        if kind == "dormant_with_vera":
            body = f"{name}, it’s been a while since Vera last helped on your account. I found one concrete item worth checking now. Want me to show it?"
            return self.base(body, "open_ended", "vera", t, "Dormancy trigger uses curiosity and a single low-friction action rather than a generic sales pitch.")

        if kind == "category_seasonal":
            season = p.get("season") or "the current season"
            trends = p.get("trends") or []
            trend_text = ", ".join(str(x).replace("_", " ") for x in trends[:3])
            body = f"{name}, the supplied {season.replace('_',' ')} demand signal points to {trend_text or 'a category demand shift'}."
            if p.get("shelf_action_recommended"):
                body += " The data also recommends a shelf adjustment. Want me to turn the strongest demand signal into a simple stock/listing action?"
            else:
                body += " Want me to turn the strongest signal into one concrete action?"
            return self.base(body, "open_ended", "vera", t, "Category trend is interpreted from the supplied demand shifts and converted into one actionable decision.")

        if kind == "cde_opportunity":
            digest_id = p.get("digest_item_id")
            item = next((d for d in c.get("digest", []) if d.get("id") == digest_id), None) if digest_id else None
            title = item.get("title") if item else None
            source = item.get("source") if item else None
            credits = p.get("credits")
            fee = p.get("fee")
            body = f"{name}, there’s a relevant CDE opportunity"
            if title: body += f": {title}"
            if source: body += f" ({source})"
            if credits: body += f" — {credits} credit(s)"
            if fee: body += f", {str(fee).replace('_',' ')}"
            body += ". Want me to prepare the details for review?"
            return self.base(body, "open_ended", "vera", t, "External education opportunity is grounded in the supplied digest item and trigger terms.")

        if kind == "festival_upcoming":
            festival = p.get("festival") or "the upcoming festival"
            date = p.get("date")
            days = p.get("days_until")
            relevant = p.get("category_relevance") or []
            if relevant and c.get("slug") not in relevant:
                return self.base(f"{name}, the upcoming {festival} is not marked as a relevant category moment in the supplied data, so I would not push a campaign now.", "none", "vera", t, "Festival is not marked relevant to this category; explicitly recommending no campaign.")
            body = f"{name}, {festival} is coming"
            if date: body += f" on {date}"
            if days is not None: body += f" ({days} days away)"
            body += ". Want me to identify one category-fit action using your existing offer/data?"
            return self.base(body, "open_ended", "vera", t, "Seasonal trigger is used only when the category is explicitly relevant and is tied to existing merchant context.")

        if kind == "milestone_reached":
            metric = p.get("metric") or "metric"
            now_value = p.get("value_now")
            target = p.get("milestone_value")
            body = f"{name}, your {metric.replace('_',' ')} is at {now_value}"
            if target: body += f" and the next milestone is {target}"
            body += ". Want me to turn that progress into one customer-facing post?"
            return self.base(body, "open_ended", "vera", t, "Milestone message uses the current value and target supplied by the trigger.")

        if kind in {"appointment_tomorrow", "customer_lapsed_soft"}:
            if kind == "appointment_tomorrow":
                body = f"Hi {first_name((m.get('identity') or {}).get('name'))} — {m.get('identity',{}).get('name','the business')} here. You have an appointment reminder for tomorrow in the supplied schedule. Reply YES if you want us to confirm it."
                return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Appointment reminder is customer-facing and uses only the fact that tomorrow's appointment trigger is active.")
            body = f"Hi {first_name((m.get('identity') or {}).get('name'))} — {m.get('identity',{}).get('name','the business')} here. We noticed you have not visited recently. Want us to help with a simple next-step option? Reply YES."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Soft-lapse outreach is consent-gated and intentionally lower pressure than a hard-winback message.")

        if kind == "recall_due":
            customer_name = first_name(((t.get("payload") or {}).get("customer_name")) or "")
            body = f"Hi {customer_name if customer_name != 'there' else 'there'} — {m.get('identity',{}).get('name','the business')} here. Your scheduled follow-up/recall reminder is due. Reply YES if you want us to continue."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Generic recall trigger has insufficient domain-specific detail, so the message avoids inventing a medical/service claim.")

        # Generic fallback remains grounded and intentionally modest.
        body = f"{name}, I have a new {kind.replace('_',' ')} signal for your account. Want me to turn it into one concrete next step?"
        return self.base(body, "open_ended", "vera", t, f"Fallback for {kind}; no unsupported fact was introduced.")

    def _customer(self, c, m, t, customer, packet):
        p = t.get("payload") or {}
        kind = t.get("kind", "")
        mi = m.get("identity") or {}
        ci = customer.get("identity") or {}
        customer_name = ci.get("name") or first_name(ci.get("phone_redacted"))
        merchant_name = mi.get("name", "the business")
        owner = mi.get("owner_first_name") or first_name(merchant_name)
        offer = best_offer(m)
        offer_text = offer.get("title") if offer else None
        lang = language_style(ci)

        if kind == "recall_due":
            due = p.get("due_date") or p.get("recall_due_date")
            body = f"Hi {customer_name} — {owner} from {merchant_name} here. Your next dental recall is due around {due or 'now'}"
            if offer_text: body += f", and {offer_text} is currently available"
            body += ". Reply YES if you want me to help with the next appointment step."
            if "hi" in lang:
                body = f"Hi {customer_name} — {owner} from {merchant_name} here. Aapka next recall {due or 'ab'} ke around due hai"
                if offer_text: body += f"; {offer_text} bhi active hai"
                body += ". Appointment ke liye YES reply karein."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t,
                             "Consented recall outreach uses relationship continuity, due timing, actual offer and one binary action.")

        if kind == "customer_lapsed_hard":
            days = p.get("days_since_last_visit")
            focus = p.get("previous_focus")
            body = f"Hi {customer_name} 👋 {owner} from {merchant_name} here. It’s been about {days or 'a while'} days since your last visit"
            if focus: body += f"; we remember your focus was {str(focus).replace('_',' ')}"
            body += ". We have an option that may fit that goal. Want me to hold a trial spot? Reply YES — no commitment."
            if "hi" in lang:
                body = f"Hi {customer_name} 👋 {owner} from {merchant_name} here. Aapki last visit ko lagbhag {days or 'kuch'} din ho gaye"
                if focus: body += f"; aapka focus {str(focus).replace('_',' ')} tha"
                body += ". Ek suitable option hai. Trial spot hold karun? YES reply karein — no commitment."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t,
                             "Lapsed customer has consent; message is warm, non-shaming and tied to known prior intent.")

        if kind == "trial_followup":
            options = p.get("next_session_options") or []
            slot = options[0].get("label") if options and isinstance(options[0], dict) else None
            body = f"Hi {customer_name} — {merchant_name} here. Following up on your trial"
            if p.get("trial_date"): body += f" from {p['trial_date']}"
            if slot: body += f". We have {slot} available"
            body += ". Want me to hold it for you? Reply YES."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Trial follow-up uses the actual trial date/slot and one binary commitment.")

        if kind == "wedding_package_followup":
            wedding = p.get("wedding_date")
            body = f"Hi {customer_name} 💍 {owner} from {merchant_name} here. Your wedding date is {wedding or 'coming up'}"
            if offer_text: body += f" and our current {offer_text} may fit the prep window"
            body += ". Want me to block a first consultation slot? Reply YES."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Bridal follow-up is tied to the customer's known wedding date and actual merchant offer.")

        if kind == "chronic_refill_due":
            meds = p.get("medicines") or p.get("molecule_list") or []
            runout = p.get("run_out_date") or p.get("stock_runs_out_iso")
            total = p.get("total")
            savings = p.get("savings")
            body = f"Namaste — {merchant_name}. Your saved refill list includes {', '.join(meds) if isinstance(meds,list) else meds} and is due around {runout or 'the supplied date'}"
            if total is not None: body += f". Total: {money(total)}"
            if savings is not None: body += f"; savings: {money(savings)}"
            body += ". Reply CONFIRM if you want us to prepare the refill."
            return self.base(body, "CONFIRM/STOP", "merchant_on_behalf", t, "Refill outreach uses precise medicine/date/price facts and a single dispatch confirmation.")

        if kind == "appointment_tomorrow":
            body = f"Hi {customer_name} — {merchant_name} here. This is a reminder that your appointment is tomorrow. Reply YES if you want us to confirm it."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Appointment reminder is a consented, time-sensitive customer action with one binary CTA.")

        if kind == "customer_lapsed_soft":
            body = f"Hi {customer_name} — {merchant_name} here. We haven’t seen you recently. If you’d like to come back, reply YES and we’ll help with the next simple step."
            return self.base(body, "YES/STOP", "merchant_on_behalf", t, "Soft lapse uses a low-pressure, consented reactivation message without inventing an offer.")

        return self.base(f"Hi {customer_name} — {merchant_name} here. We have a relevant update for you. Reply YES if you'd like us to continue.",
                         "YES/STOP", "merchant_on_behalf", t, "Customer message fallback uses consent and one binary action.")

    def _guardrail(self, body, category, packet):
        # Remove obvious model-introduced unsupported certainty. Do not over-edit a valid deterministic draft.
        taboos = [str(x).lower() for x in packet.get("policy", {}).get("taboos", [])]
        lower = body.lower()
        for taboo in taboos:
            if taboo and taboo in lower:
                body = re.sub(re.escape(taboo), "", body, flags=re.I)
        # Avoid accidental multiple CTA questions from the LLM.
        # Keep the final body concise enough for WhatsApp readability.
        return re.sub(r"\s{2,}", " ", body).strip()
