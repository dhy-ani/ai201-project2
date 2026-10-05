# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search is a plain keyword match, and the query parser is regex plus a
stopword strip, so an odd phrasing can leave a description that matches nothing.
Two of the three tools also call a model, which can fail or return an empty
caption. 5 of 5 would punish me for things outside my control. 4 of 5 still
means the normal path works.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never touches the model. The branch in `run_agent` is a plain
empty-list check on the output of a filter written in ordinary Python, so the
same input gives the same result every time. If it misses once, that is a bug
in my code, not noise.

---

## 3. The selected item is the one `suggest_outfit` receives

Across 5 runs of a matching query, the `new_item` that arrives at
`suggest_outfit` has the same `title` and `price` as `session["selected_item"]`
in 5 of 5 runs. I check by printing `new_item` at the top of `suggest_outfit`
and comparing it to the session after the run.

**Why this target:**
State handling is plain dictionary reads and writes with no model in the path,
so there is nothing random to excuse a mismatch. A mismatch would mean the loop
passed a stale or wrong item, which is the exact failure the session exists to
prevent. Anything under 5 of 5 means the session is broken.

---

## 4. The fit card is postable and mentions the price

For 5 different items, at least 4 of 5 fit cards are 200 characters or fewer
and contain the item's price.

**Why this target:**
The caption comes from a model, so the wording changes between runs and I can't
require exact text. Length and the price are things I can count. I allow one
miss in 5 because a model at a nonzero temperature will occasionally run long or
leave the price out, and requiring 5 of 5 would mostly measure luck. I don't
check tone here because I can't score it with a number.

---

## 5. The price ceiling is respected

For 5 queries that each include a max price, every listing `search_listings`
returns costs no more than that ceiling, in 5 of 5 queries. A listing priced
exactly at the ceiling counts as a match.

**Why this target:**
The price filter is a single comparison in `search_listings`, with no model and
no parsing ambiguity once `max_price` is a float. It has to be 5 of 5 because
one result over the limit means the user sees something they said they
couldn't afford. The one place it can break is the parser reading the wrong
number out of the query, so the test queries should include a size number too.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->