"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    # ── Criterion 1: a matching query completes all three tools ──────────────
    {
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },

    # ── Criterion 2: an impossible query stops before the second tool ────────
    # Nothing in the 40 listings is a ballgown, and nothing at all is under $5,
    # so this fails on three filters at once rather than squeaking past one.
    {
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },

    # ── Criterion 3: the selected item is the one suggest_outfit receives ────
    # Any matching query works — what is being checked is what ends up in the
    # session, not what the user typed. A query with a size in it is used on
    # purpose, so the parsed size has to survive the trip too.
    {
        "name": "session carries the selected item",
        "query": "90s track jacket size M",
        "wardrobe": "example",
        "criterion": 3,
    },

    # ── Criteria 4 and 5: five different items, five different ceilings ──────
    # Criterion 4 says "for 5 DIFFERENT items", so these are five scenarios
    # rather than one scenario run five times — five tries of one query would
    # measure the model's variance on a single item, which is not what the
    # criterion says.
    #
    # The same five runs are also criterion 5's evidence. Criterion 5 is about
    # what search_listings returns, and every one of these queries carries a
    # max price, so each run produces both a fit card to measure and a result
    # list to check against a ceiling. Two criteria, one set of runs, because
    # they ask about different stages of the same run.
    {
        "name": "fit card — vintage band tee ($19, ceiling $30)",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — denim jacket ($42, ceiling $50)",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — silk slip dress ($30, ceiling $45)",
        "query": "silk slip dress under $45",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — platform sneakers ($48, ceiling $60)",
        "query": "platform sneakers size 8 under $60",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — leather belt ($12, ceiling $25)",
        "query": "leather belt under $25",
        "wardrobe": "example",
        "criterion": 4,
    },

    # ── Diagnostic: one of unit 4's three failure modes ──────────────────────
    # Not one of the five criteria. A user with nothing saved should still get
    # general styling advice rather than a crash or an empty string.
    {
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
