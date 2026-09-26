# How to beat a generic AI submission

## 1. Decision quality — highest leverage

Do not ask the LLM to choose the action. `ranker.py` chooses it.

The ranker should prefer:

1. explicit merchant intent
2. urgent operational/compliance issues
3. consented customer deadlines
4. severe merchant-specific performance changes
5. fresh category/research signals
6. generic engagement only when the merchant is receptive

It should also be able to say **do nothing** when:

- customer consent is missing
- trigger expired
- category relevance is false
- repeated unanswered nudges make another touch counterproductive
- the context contains insufficient evidence

## 2. Specificity

Use facts with provenance.

Good:

`Calls are down 50% over 7 days.`

Better:

`Calls are down 50% over 7 days; your active offer is Dental Cleaning @ ₹299.`

Best when justified by context:

`22 chronic-Rx customers were dispensed the recalled batch.`

Never calculate a number unless the inputs support it. Add the source to `FactSelector`.

## 3. Category fit

Put vocabulary and taboos in `policies.py` and the category context. The model should not invent the domain rules.

Dentist: clinical/precise.

Restaurant: covers, delivery, AOV.

Gym: retention, attendance, trial.

Pharmacy: batch, refill, dispensed, replacement.

Salon: bridal, service, package, visual demand.

## 4. Merchant fit

Prefer facts that identify the merchant:

- owner first name
- locality
- existing offer
- actual metric
- prior conversation intent
- recent review theme
- subscription state

Do not say `run a discount` if there is an existing offer you can use.

## 5. Engagement compulsion

Use one lever per message:

- specificity
- loss aversion
- social proof
- effort externalization
- curiosity
- reciprocity
- asking the merchant
- single binary commitment

Do not stack five CTAs.

## 6. The contrarian rule

If the data says a popular event is likely to hurt the merchant, do not blindly promote it.

Example logic:

`IPL today + Saturday + supplied peer effect = covers down`

=> recommend using an existing delivery offer rather than a match-night dine-in promotion.

This is the clearest example in the case studies of the judge rewarding business judgment rather than text quality.

## 7. Conversation advantage

After `yes`, stop selling.

Move to execution:

`Great — I’ll prepare the draft using the details already shared.`

After `no`:

`end`

After an auto-reply:

`wait`

After `later`:

`wait`

After an unclear message:

`wait` rather than another unsolicited pitch.

## 8. How to iterate from judge scores

If Decision Quality is low:
- change `ranker.py`
- inspect which trigger should have won
- add negative/suppression rules

If Specificity is low:
- change `fact_selector.py`
- expose more real numbers, dates, offers, sources

If Category Fit is low:
- change `policies.py`
- change the category branch in `composer.py`

If Merchant Fit is low:
- add merchant-specific facts to `FactSelector`
- prefer owner/locality/offer/history/performance

If Engagement is low:
- change the CTA strategy
- use a single low-effort action
- consider reciprocity or asking-the-merchant

Never fix a score by hardcoding the exact canonical example.
