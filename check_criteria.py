#!/usr/bin/env python3
"""
Score the five criteria, one row each. ← UNIT 4, MILESTONE 3

    python check_criteria.py --label before
    python check_criteria.py --label after

`run_eval.py` writes one block per SCENARIO and leaves the verdicts blank,
because deciding what counts as a pass depends on criteria it cannot read.
This file is where that decision lives, written down as code rather than as me
reading output and forming an impression.

What each criterion needs is not the same shape of check, which is the reason
this is not one loop:

  1  needs the whole run to finish          -> needs the model
  2  needs the run to STOP, and to prove    -> no model: the branch fires
     suggest_outfit never ran                  before the first model call
  3  needs the argument suggest_outfit      -> no model: the argument is
     actually received                         recorded before the call returns
  4  needs the generated caption            -> needs the model
  5  needs what search_listings returned    -> no model: search runs first

So 2, 3 and 5 are measurable in an environment with no GEMINI_API_KEY, and 1
and 4 are not. They are reported as "not measured". They are not estimated,
and they are not marked passed on the grounds that they probably would.

Criterion 3's check is the one the criterion itself describes: "I check by
printing new_item at the top of suggest_outfit and comparing it to the session
after the run." Rather than leaving a print in the tool, `_recording` wraps the
function the loop actually calls and keeps what it was handed. The wrap goes on
`agent.suggest_outfit` and not `tools.suggest_outfit`, because agent.py does
`from tools import suggest_outfit` and so holds its own reference — patching
the tools module would record nothing and quietly report a pass.
"""

import argparse
import datetime as dt

import config
import scenarios as scenario_module

TRIES = 5


# ── instrumentation ──────────────────────────────────────────────────────────

def _recording(seen: list):
    """Wrap agent.suggest_outfit so the new_item it receives is kept."""
    import agent

    real = agent.suggest_outfit

    def wrapper(new_item, wardrobe):
        seen.append(new_item)
        return real(new_item, wardrobe)

    agent.suggest_outfit = wrapper
    return real


def _restore(real):
    import agent

    agent.suggest_outfit = real


def _run(query: str, wardrobe_name: str):
    """One run. Returns (session, new_item_seen_by_suggest_outfit)."""
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    wardrobe = get_empty_wardrobe() if wardrobe_name == "empty" else get_example_wardrobe()

    seen: list = []
    real = _recording(seen)
    try:
        session = run_agent(query, wardrobe)
    finally:
        _restore(real)

    return session, (seen[0] if seen else None)


def _scenarios_for(number):
    return [s for s in scenario_module.SCENARIOS if s.get("criterion") == number]


# ── criterion 2: the branch ──────────────────────────────────────────────────

def check_2():
    """An impossible query stops before suggest_outfit. Target 5 of 5."""
    scenario = _scenarios_for(2)[0]
    rows = []
    for _ in range(TRIES):
        session, seen = _run(scenario["query"], scenario["wardrobe"])
        passed = (
            bool(session.get("error"))                     # it stopped
            and seen is None                               # suggest_outfit never called
            and session.get("outfit_suggestion") is None
            and session.get("fit_card") is None
            and not session.get("search_results")
        )
        rows.append({
            "pass": passed,
            "detail": (
                f"stopped={bool(session.get('error'))}, "
                f"suggest_outfit_called={seen is not None}, "
                f"results={len(session.get('search_results') or [])}"
            ),
            "message": session.get("error"),
        })
    return rows


# ── criterion 3: the session carries the selected item ───────────────────────

def check_3():
    """new_item at suggest_outfit matches session['selected_item']. Target 5 of 5."""
    scenario = _scenarios_for(3)[0]
    rows = []
    for _ in range(TRIES):
        session, seen = _run(scenario["query"], scenario["wardrobe"])
        selected = session.get("selected_item")

        if seen is None or selected is None:
            rows.append({
                "pass": False,
                "detail": "suggest_outfit was never reached — nothing to compare",
                "message": session.get("error"),
            })
            continue

        same = (
            seen.get("title") == selected.get("title")
            and float(seen.get("price")) == float(selected.get("price"))
        )
        rows.append({
            "pass": same,
            "detail": (
                f"received {seen.get('title')!r} (${seen.get('price')}) · "
                f"session {selected.get('title')!r} (${selected.get('price')})"
            ),
            "message": None,
        })
    return rows


# ── criterion 5: the price ceiling ───────────────────────────────────────────

def check_5():
    """Every listing returned costs no more than the ceiling. Target 5 of 5 queries.

    The five tries are five different QUERIES, not five repeats of one — the
    criterion says "for 5 queries that each include a max price". Search is
    deterministic, so repeating one query five times would be one measurement
    printed five times.
    """
    from agent import parse_query

    rows = []
    for scenario in _scenarios_for(4):          # the five ceiling queries
        session, _ = _run(scenario["query"], scenario["wardrobe"])
        ceiling = parse_query(scenario["query"])["max_price"]
        results = session.get("search_results") or []
        over = [r for r in results if float(r["price"]) > float(ceiling)]

        rows.append({
            "pass": ceiling is not None and not over,
            "detail": (
                f"ceiling ${ceiling:g} · {len(results)} returned · "
                f"{len(over)} over" + (f" ({[r['title'] for r in over]})" if over else "")
                + (f" · dearest ${max(float(r['price']) for r in results):g}" if results else "")
            ),
            "message": scenario["query"],
        })
    return rows


# ── criteria needing the model ───────────────────────────────────────────────

def not_measured(reason):
    return [{"pass": None, "detail": reason, "message": None} for _ in range(TRIES)]


# ── report ───────────────────────────────────────────────────────────────────

def verdict(rows, target):
    if any(r["pass"] is None for r in rows):
        return "NOT TESTED"
    passed = sum(bool(r["pass"]) for r in rows)
    return f"{'MET' if passed >= target else 'MISSED'} ({passed}/{len(rows)})"


def cell(row):
    return {True: "PASS", False: "FAIL", None: "n/m"}[row["pass"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    config.CACHE_ENABLED = False
    print("Cache is OFF.\n")

    no_key = "needs a generated answer; no GEMINI_API_KEY in this environment"

    results = [
        (1, "A matching query completes all three tools", 4,
         not_measured(no_key)),
        (2, "An impossible query stops before the second tool", 5, check_2()),
        (3, "The selected item is the one suggest_outfit receives", 5, check_3()),
        (4, "The fit card is <=200 chars and mentions the price", 4,
         not_measured(no_key)),
        (5, "The price ceiling is respected", 5, check_5()),
    ]

    for number, name, target, rows in results:
        print(f"{number}. {name}")
        print(f"   {verdict(rows, target)}  [{', '.join(cell(r) for r in rows)}]")
        for row in rows:
            print(f"     - {row['detail']}")
        print()

    write(results, args)


def write(results, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"criteria_{stamp}{label}.md"

    heads = " | ".join(f"Try {i}" for i in range(1, TRIES + 1))
    div = "|".join(["---"] * TRIES)

    lines = [
        f"# Criteria run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `check_criteria.py::main`",
        "- Loop: `agent.py::run_agent` · search via MCP: "
        f"{config.USE_MCP} · tools: `tools.py`",
        f"- Tries per criterion: {TRIES}, caching off",
        f"- Temperature: {config.TEMPERATURE}",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"| Criterion | Target | {heads} | Verdict |",
        f"|---|---|{div}|---|",
    ]

    targets = {1: "4 of 5", 2: "5 of 5", 3: "5 of 5", 4: "4 of 5", 5: "5 of 5"}
    for number, name, target, rows in results:
        cells = " | ".join(cell(r) for r in rows)
        lines.append(f"| {number}. {name} | {targets[number]} | {cells} | {verdict(rows, target)} |")

    lines += [
        "",
        "`n/m` = not measured. Criteria 1 and 4 read a model-generated answer and",
        "there is no `GEMINI_API_KEY` in this environment, so they were not run",
        "rather than estimated.",
        "",
        "## What each try actually saw",
        "",
    ]

    for number, name, target, rows in results:
        lines += [f"### Criterion {number} — {name}", ""]
        for i, row in enumerate(rows, 1):
            lines.append(f"- **Try {i}** — {cell(row)}: {row['detail']}")
        if any(r["message"] for r in rows):
            first = next(r["message"] for r in rows if r["message"])
            lines += ["", "Message / query from try 1:", "", "```", str(first), "```"]
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
