"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from mcp_client import MCPError, call_tool
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────
#
# Regex and a stopword strip. No model call — this runs on every query including
# the ones that stop at the branch, and paying for a model call to find the
# digits in "under $30" would be absurd.

# Words that say how the user is asking rather than what they want. Stripping
# them matters because search_listings scores on keyword overlap: leaving
# "looking" in the description means a listing containing "looking" scores a
# point for nothing.
_STOPWORDS = {
    "a", "an", "and", "any", "are", "around", "at", "below", "budget", "but",
    "can", "cheap", "do", "find", "for", "get", "got", "have", "i", "id",
    "im", "in", "is", "it", "less", "like", "looking", "max", "maximum", "me",
    "my", "need", "no", "of", "on", "or", "please", "search", "show", "size",
    "some", "something", "than", "that", "the", "to", "under", "up", "us",
    "want", "with", "would", "you",
}

# "under $30", "below 30", "less than 40", "max $25", "up to 30", "no more than 30"
_PRICE_PHRASE = re.compile(
    r"\b(?:under|below|less\s+than|max(?:imum)?|up\s+to|at\s+most|no\s+more\s+than)"
    r"\s*\$?\s*(\d+(?:\.\d+)?)",
    re.I,
)
# A bare "$30" anywhere.
_PRICE_DOLLAR = re.compile(r"\$\s*(\d+(?:\.\d+)?)")

# "size M", "size 8", "size US 9", "size W30", "size 8.5"
_SIZE_PHRASE = re.compile(
    r"\bsize\s+(?:us\s+)?([a-z]{1,3}\d*(?:/[a-z]{1,3})?|\d+(?:\.\d+)?)", re.I
)
# "US 9" without the word "size".
_SIZE_US = re.compile(r"\bus\s*(\d+(?:\.\d+)?)\b", re.I)
# "W30" waist sizing, without the word "size".
_SIZE_WAIST = re.compile(r"\bw(\d{2})\b", re.I)
# Bare XS / XL / XXL. Deliberately NOT bare S, M or L: "m" and "s" turn up
# inside ordinary queries far too often to read as a size.
_SIZE_BARE = re.compile(r"\b(xxs|xs|xl|xxl)\b", re.I)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max price out of plain language.

    Returns a dict with keys `description` (str), `size` (str or None) and
    `max_price` (float or None) — always all three keys, so the caller never
    has to guess whether a field is missing or merely absent.

    The ordering matters and is the thing most likely to break: the price is
    taken out of the text BEFORE the size is looked for, because
    "platform sneakers size 8 under $40" has two numbers in it, and reading the
    8 as a price or the 40 as a size is the obvious way to get this wrong.
    Criterion 5 is about exactly that.
    """
    text = str(query or "")

    # 1. Price first, and remove the phrase it matched so those digits can't be
    #    read a second time as a size.
    max_price = None
    match = _PRICE_PHRASE.search(text) or _PRICE_DOLLAR.search(text)
    if match:
        max_price = float(match.group(1))
        text = text[: match.start()] + " " + text[match.end() :]

    # 2. Size, from the most explicit form to the least.
    size = None
    for pattern, template in (
        (_SIZE_PHRASE, "{}"),
        (_SIZE_US, "US {}"),
        (_SIZE_WAIST, "W{}"),
        (_SIZE_BARE, "{}"),
    ):
        match = pattern.search(text)
        if match:
            size = template.format(match.group(1)).upper()
            text = text[: match.start()] + " " + text[match.end() :]
            break

    # 3. Whatever is left, minus the stopwords, is the description.
    words = [w for w in re.findall(r"[A-Za-z0-9']+", text) if w.lower() not in _STOPWORDS]
    description = " ".join(words).strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The branch rule, stated once: if `search_listings` comes back empty, write
    a message into session["error"] naming the description, size and ceiling it
    actually tried and what to loosen, then return — without calling
    `suggest_outfit`. Otherwise take the first result as the selected item and
    carry on through `suggest_outfit` and `create_fit_card`.

    Every tool reads its input out of the session rather than from the previous
    return value. That is slightly more code and it is the only reason
    criterion 3 can be checked at all — you cannot print a variable you have
    already overwritten.
    """
    trace.start_trace()
    session = new_session(query, wardrobe)
    steps = 0

    # ── step 1: parse ────────────────────────────────────────────────────────
    steps += 1
    trace.check_iterations(steps)

    session["parsed"] = parse_query(query)
    description = session["parsed"]["description"]
    size = session["parsed"]["size"]
    max_price = session["parsed"]["max_price"]

    trace.step(
        "parse_query",
        inputs=query,
        returned=session["parsed"],
        note="regex for size and price, stopword strip for the description",
    )

    # ── step 2: search ───────────────────────────────────────────────────────
    steps += 1
    trace.check_iterations(steps)

    search_inputs = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    via = "search_listings (via MCP)" if config.USE_MCP else "search_listings (direct call)"

    try:
        if config.USE_MCP:
            results = call_tool("search_listings", search_inputs)
        else:
            results = search_listings(description, size, max_price)
    except MCPError as exc:
        # The MCP server is a separate process. If it cannot be started or it
        # refuses the call, that is not the same failure as "nothing matched",
        # and saying "no listings found" here would be a lie.
        session["error"] = (
            f"Couldn't reach the search tool over MCP, so nothing was searched. "
            f"This is a problem with the tool server, not with your query — "
            f"try again, and if it keeps happening run `python mcp_server.py` "
            f"on its own to see why it won't start.\n  (underlying error: {exc})"
        )
        trace.step(via, inputs=search_inputs, returned=None,
                   note="MCP unreachable — stopping")
        return session

    session["search_results"] = results or []

    trace.step(
        via,
        inputs=search_inputs,
        returned=session["search_results"],
        note=f"{len(session['search_results'])} match(es)",
    )

    # ── THE BRANCH ───────────────────────────────────────────────────────────
    if not session["search_results"]:
        tried = [f'description "{description or "(nothing)"}"']
        if size:
            tried.append(f"size {size}")
        if max_price is not None:
            tried.append(f"under ${max_price:g}")

        session["error"] = (
            "Nothing in the listings matches "
            + ", ".join(tried)
            + ". Try raising the price ceiling, dropping the size, or using "
            "plainer words for the item — \"jacket\" finds more than "
            "\"cropped moto jacket\"."
        )
        trace.step(
            "branch: search_results is empty",
            returned=None,
            note="stopping before suggest_outfit — the loop ends here",
        )
        return session

    # ── step 3: select ───────────────────────────────────────────────────────
    steps += 1
    trace.check_iterations(steps)

    session["selected_item"] = session["search_results"][0]
    trace.step(
        "select_item",
        inputs=f"{len(session['search_results'])} candidates, taking the best-scored",
        returned=session["selected_item"],
        note="written to session['selected_item']",
    )

    # ── step 4: suggest_outfit ───────────────────────────────────────────────
    steps += 1
    trace.check_iterations(steps)

    owned = len((session["wardrobe"] or {}).get("items") or [])
    try:
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
    except ModelUnavailable as exc:
        session["error"] = (
            f"Found \"{session['selected_item'].get('title')}\" but couldn't reach "
            f"the model to style it, so there's no outfit or caption. The search "
            f"worked — it's the writing step that failed. Check your "
            f"GEMINI_API_KEY in .env, then run the same query again.\n"
            f"  (underlying error: {exc})"
        )
        trace.step("suggest_outfit", inputs=session["selected_item"], returned=None,
                   note="ModelUnavailable — stopping, search result kept")
        return session

    trace.step(
        "suggest_outfit",
        inputs={"new_item": session["selected_item"],
                "wardrobe_items": owned},
        returned=session["outfit_suggestion"],
        note="general advice (empty wardrobe)" if owned == 0 else f"{owned} owned pieces offered",
    )

    # ── step 5: create_fit_card ──────────────────────────────────────────────
    steps += 1
    trace.check_iterations(steps)

    try:
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
    except ModelUnavailable as exc:
        session["error"] = (
            f"Got as far as the outfit for \"{session['selected_item'].get('title')}\" "
            f"but couldn't reach the model to write the caption. The outfit above "
            f"is still good. Check your GEMINI_API_KEY in .env and run it again.\n"
            f"  (underlying error: {exc})"
        )
        trace.step("create_fit_card", inputs=session["selected_item"], returned=None,
                   note="ModelUnavailable — stopping, outfit kept")
        return session

    trace.step(
        "create_fit_card",
        inputs={"outfit": session["outfit_suggestion"],
                "new_item": session["selected_item"]},
        returned=session["fit_card"],
        note=f"{len(session['fit_card'] or '')} characters",
    )

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
