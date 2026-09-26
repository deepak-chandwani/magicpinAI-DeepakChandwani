"""Category-specific rules. Keep business policy here, not in the LLM prompt."""

POLICIES = {
    "dentists": {
        "tone": "peer-clinical, precise, warm",
        "allowed_terms": ["fluoride varnish", "caries", "recall", "aligners", "whitening", "clinical"],
        "avoid": ["cure", "guaranteed", "miracle", "100% effective"],
        "preferred_ctas": ["draft", "review", "send", "prepare"],
    },
    "salons": {
        "tone": "warm operator-to-operator, visual and practical",
        "allowed_terms": ["bridal", "trial", "hair spa", "balayage", "skin prep", "package"],
        "avoid": ["guaranteed result", "permanent", "instant transformation"],
        "preferred_ctas": ["draft", "feature", "block", "prepare"],
    },
    "restaurants": {
        "tone": "commercial, concise, operator-to-operator",
        "allowed_terms": ["covers", "AOV", "delivery", "dine-in", "weekday", "weekend", "banner"],
        "avoid": ["guaranteed sales", "viral", "everyone will"],
        "preferred_ctas": ["draft", "push", "feature", "prepare"],
    },
    "gyms": {
        "tone": "coach-like, practical, no-shame",
        "allowed_terms": ["members", "retention", "trial", "class", "attendance", "conversion"],
        "avoid": ["shame", "lazy", "guaranteed weight loss", "instant results"],
        "preferred_ctas": ["draft", "hold", "prepare", "launch"],
    },
    "pharmacies": {
        "tone": "trustworthy, precise, compliance-first",
        "allowed_terms": ["batch", "refill", "dispensed", "replacement", "chronic-Rx", "stock"],
        "avoid": ["cure", "guaranteed", "panic", "safe for everyone"],
        "preferred_ctas": ["draft", "prepare", "check", "pull"],
    },
}


def policy_for(category):
    return POLICIES.get(category.get("slug"), {
        "tone": "concise and factual",
        "allowed_terms": [],
        "avoid": ["guaranteed", "everyone", "100%"],
        "preferred_ctas": ["draft", "prepare"],
    })
