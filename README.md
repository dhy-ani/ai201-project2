# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr takes a plain-language request like "vintage graphic tee under $30, size M" and searches a listings file for matches. It picks the top result, suggests outfits that pair it with the user's wardrobe, and writes a short caption they could post. If nothing matches, it stops and says what to change instead of running the later steps.

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, write a message to `session["error"] ` naming the description, size, and price it tried and what to loosen, then stop. Otherwise, store the first result as `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex for size and max price, then a stopword strip for the description (`agent.py::parse_query`). No model call.

**What moves through the session:** `query` -> `parsed` -> `search_results` -> `selected_item` -> `outfit_suggestion` -> `fit_card`. `error` is set only when the run stops early. Each tool reads its input from the session, not from the previous return value.

---

## Tool Inventory

### `search_listings`

- **What it does:** Filters the 40 listings in `data/listings.json` by size and
  price, scores whatever survives by keyword overlap with the description, and
  returns the best matches first. A keyword hit in the `title` counts double. It
  is a keyword match, not a semantic one — "outerwear" will not find a listing
  that only ever says "jacket".
- **Inputs:** `description` (str, required), `size` (str or None — a letter
  size `"M"`, a US shoe size `"US 9"`, or a waist `"W30"`), `max_price` (float
  or None, US dollars, inclusive).
- **Returns:** `list[dict]`, at most `config.SEARCH_RESULT_LIMIT` (10) long,
  best match first. Each dict has `id` (str), `title` (str), `description`
  (str), `category` (str: tops / bottoms / outerwear / shoes / accessories),
  `style_tags` (list[str]), `size` (str), `condition` (str: excellent / good /
  fair), `price` (float), `colors` (list[str]), `brand` (str or None),
  `platform` (str: depop / thredUp / poshmark).
- **When it has nothing:** returns `[]`. Not None, not an exception — the empty
  list is a normal successful result meaning the filters excluded everything or
  no listing shared a keyword. `run_agent` branches on exactly this.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the
  selected listing. With wardrobe items it names specific pieces the user owns;
  with none it gives general styling advice using common basics.
- **Inputs:** `new_item` (dict — one listing, as `search_listings` returns
  them), `wardrobe` (dict with an `items` key holding a list; items may be
  dicts or plain strings).
- **Returns:** `str`, always non-empty.
- **When it has nothing:** an empty wardrobe is not an error — it switches the
  prompt to general advice. If the model returns an empty string, the tool
  falls back to a fixed sentence rather than returning `""`, so the caller
  never has to handle an empty success. If the model is unreachable it raises
  `ModelUnavailable`, which `run_agent` catches.

### `create_fit_card`

- **What it does:** Asks the model for a short social caption about the find,
  mentioning the item, its price and the platform once each.
- **Inputs:** `outfit` (str — what `suggest_outfit` returned), `new_item` (dict
  — the same listing).
- **Returns:** `str`, aimed at two sentences and under 200 characters. The
  length is requested in the prompt, not enforced in code, which is why
  criterion 4 measures it rather than assuming it.
- **When it has nothing:** if `outfit` is empty or whitespace it returns the
  message "No outfit to write a caption for yet. Run suggest_outfit first."
  rather than raising. If the model is unreachable it raises
  `ModelUnavailable`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* Implementations of all three tools in `tools.py`, using the spec: filter on all three inputs, return `[]` on no match, general advice for an empty wardrobe.
- *What came back:* A `search_listings` that filtered on size, price, and keywords, plus two model-backed tools. It guessed the loader and adapter names and treated the wardrobe as a list of strings.
- *What I changed:* [your real changes, e.g. the actual loader and adapter names, and reading the wardrobe dict's real key instead of iterating the dict]

**Moment 2**

- *What I asked for:* `run_agent()` following my branch rule, with every result going through the session.
- *What came back:* A loop that checks the session each pass to pick the next step, a regex query parser, and a no-match message naming the query and what to change. `suggest_outfit` returned a list, so it passed the first outfit string to `create_fit_card`.
- *What I changed:* [your real changes, e.g. parser edge cases you found, or the message wording. If you changed nothing, say that.]

---

# Unit 4 — The Test

## Before anything else: two things that shaped this unit

**1. The unit 3 loop did not exist.** `agent.py::run_agent` was still the
starter's TODO stub — `session["error"] = "The planning loop isn't built yet"`
— and `agent.py::parse_query`, which the Planning Loop section above already
described, had never been written. Nothing in unit 4 runs without them, so both
were built at the start of this unit. **That is unit 3 catch-up, not unit 4's
one allowed change.** The one change this unit is the improvement in Milestone
5, and it is named as such below. The commit history separates them.

**2. There is no `GEMINI_API_KEY` in this environment.** Two of the three tools
call the model, so criteria 1 and 4 cannot be measured. They are reported as
**NOT TESTED** everywhere below — not estimated, not inferred, and not marked
MET on the grounds that they probably would be. Criteria 2, 3 and 5 are
measurable without a key, because each of them is about a stage that runs
before the first model call, and all three were measured properly, five tries
each.

This also means the third failure mode was not simulated. It is the live state
of the environment, which is why the message in the trace below is real output
rather than something produced by breaking a key on purpose.

## MCP: what changed in the code

`search_listings` is the tool that moved. It is registered in `mcp_server.py`
with typed inputs and a description written for an agent that will never see
the implementation — units on `max_price` ("a number rather than a string and
with no currency symbol — 30 or 29.99, never `"$30"`"), the inclusive ceiling,
how token-wise size matching treats `"M"` against `"S/M"` and `"L"` against
`"XL"`, every key and type in the returned objects, and the empty array spelled
out as a normal result that a caller should not retry.

In `agent.py::run_agent` the direct call became:

```python
results = call_tool("search_listings", {
    "description": description, "size": size, "max_price": max_price,
})
```

**Did anything behave differently? No — and I checked rather than assuming.**
`config.USE_MCP` keeps the direct path reachable (`AI201_MCP=0`), so the two
can be compared on the same queries:

```
'vintage graphic tee under $30'       direct 10 items, mcp 10 items, equal=True, types=list/list
'platform sneakers size 8 under $40'  direct  0 items, mcp  0 items, equal=True, types=list/list
'designer ballgown size XXS under $5' direct  0 items, mcp  0 items, equal=True, types=list/list
```

Same list, same dicts, same order, including both empty cases — which was the
one I expected to differ, since an empty list is the thing most likely to come
back over a protocol as `None`, `""` or `"[]"`. `mcp_client._unwrap` is what
keeps that promise, and it is worth knowing it is there: without it the branch
in `run_agent` would be testing a string for emptiness and would quietly stop
working.

## Run Log — Before

`python check_criteria.py --label before` →
[`results/criteria_2026-10-19_0138_before.md`](results/criteria_2026-10-19_0138_before.md)
Raw per-scenario output: `python run_eval.py --label before` →
[`results/run_2026-10-19_0137_before.md`](results/run_2026-10-19_0137_before.md)

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | n/m | n/m | n/m | n/m | n/m | NOT TESTED |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The selected item is the one `suggest_outfit` receives | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is ≤200 chars and mentions the price | 4 of 5 | n/m | n/m | n/m | n/m | n/m | NOT TESTED |
| 5. The price ceiling is respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

`n/m` = not measured. Scored by `check_criteria.py::check_2`, `::check_3` and
`::check_5`.

**Criterion 2 — real output** (`check_criteria.py::check_2`, query
`designer ballgown size XXS under $5`). Identical on all five tries:

```
stopped=True, suggest_outfit_called=False, results=0
```

and the message the user sees, from `agent.py::run_agent`:

```
Nothing in the listings matches description "designer ballgown", size XXS,
under $5. Try raising the price ceiling, dropping the size, or using plainer
words for the item — "jacket" finds more than "cropped moto jacket".
```

`suggest_outfit_called=False` is the part that matters and it is not read off
the session. `check_criteria.py::_recording` wraps the function the loop
actually calls and records every invocation, so the claim "it stopped before
the second tool" is evidence rather than inference.

**Criterion 3 — real output** (`check_criteria.py::check_3`, query
`90s track jacket size M`). All five tries:

```
received '90s Track Jacket — Navy/White Stripe' ($45.0) · session '90s Track Jacket — Navy/White Stripe' ($45.0)
```

**Criterion 5 — real output** (`check_criteria.py::check_5`, five different
queries, each with its own ceiling):

```
ceiling $30 · 10 returned · 0 over · dearest $26
ceiling $50 ·  7 returned · 0 over · dearest $45
ceiling $45 ·  2 returned · 0 over · dearest $30
ceiling $60 ·  1 returned · 0 over · dearest $48
ceiling $25 ·  1 returned · 0 over · dearest $12
```

## Verdicts and Diagnoses

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Matching query completes all three tools (4 of 5) | **NOT TESTED** | `create_fit_card` needs the model. No key in this environment, so the run stops at `suggest_outfit` every time. Not marked MET. |
| 2 | Impossible query stops before the second tool (5 of 5) | **MET (5/5)** | Five for five, and checked three ways per try: the session carries an error, the search returned 0, and the wrapped `suggest_outfit` was never invoked. |
| 3 | Selected item is the one `suggest_outfit` receives (5 of 5) | **MET (5/5)** | Five for five on title and price, comparing the argument the function actually received against `session["selected_item"]` after the run. |
| 4 | Fit card ≤200 chars and mentions the price (4 of 5) | **NOT TESTED** | The fit card is the model's output. Same reason as criterion 1. |
| 5 | Price ceiling respected (5 of 5) | **MET (5/5)** | Five queries, five ceilings, zero listings over. The dearest item returned was $26 against a $30 ceiling and $45 against $50 — not close calls. |

### No measured criterion was missed. So: were the targets low?

**Yes, and I wrote down why in unit 3 without noticing what I was admitting.**
All three measurable criteria are about stages with no model in them, and my
own "why this target" notes say so in nearly those words:

- criterion 2: *"This path never touches the model… the same input gives the
  same result every time."*
- criterion 3: *"State handling is plain dictionary reads and writes with no
  model in the path, so there is nothing random to excuse a mismatch."*
- criterion 5: *"a single comparison in `search_listings`, with no model and no
  parsing ambiguity once `max_price` is a float."*

Each of those is a correct argument for setting the target at 5 of 5. It is
also, read back, an argument that the criterion cannot produce an interesting
result: a deterministic path either works or is broken, and five tries of it is
one measurement printed five times. I set three of my five criteria on the
parts of the system that cannot vary, and the two I set on the parts that can
are the two I could not run.

**The criterion I would tighten is 5**, and the tightening is already written
in my own unit 3 reasoning: *"The one place it can break is the parser reading
the wrong number out of the query, so the test queries should include a size
number too."* I identified the real risk and then did not test it — only one of
my five ceiling queries contains a second number (`platform sneakers size 8
under $60`). I would rewrite it as: *for 5 queries that each contain both a
size number and a price number, every listing returned costs no more than the
ceiling.* That version tests the parser, which is where the risk is, rather
than the comparison in `search_listings`, which is one line and was never in
doubt.

### Where the real defect was

Since nothing failed, I went looking rather than waiting, by running the parser
over sixteen phrasings a user might plausibly type. That found a genuine bug no
criterion covers.

**The step:** `agent.py::parse_query`, the parsing step, interacting with
`tools.py::_size_matches`.

**The mechanism:** the listings write waist sizes as a single token — `"W30"`,
`"W28"`, `"W30 L30"` — and `_size_matches` compares whole tokens. A user typing
the entirely natural *"jeans size 30"* produces `size="30"`, and `"30"` is not
a token of `"W30"`, so the filter excludes every pair of trousers in the file.
Search then returns `[]`, the branch fires correctly, and the agent tells the
user to loosen their query — when the actual problem was a format mismatch the
agent could have resolved itself. Seven of the forty listings are sized this
way, so the whole bottoms category was unreachable by the most obvious
phrasing for it:

```
jeans size 30 under $45         size=30   0 results
size 28 corduroy pants          size=28   0 results
straight leg trousers size 30   size=30   0 results
cargo pants size 29             size=29   0 results
carpenter jeans size 32         size=32   0 results
denim shorts size 27            size=27   0 results
```

**The pattern:** this is the same shape as the thing criterion 5's unit 3 note
warned about — the parser, not the tools, is where this agent goes wrong. The
tools are small and deterministic and they do what they say. Everything
interesting happens in the translation from what a person types to what the
tools expect, and that is the one stage I wrote no criterion about.

## Loop Trace

One full run, `python app.py ask 'jeans size 30 under $45' --trace`, after the
improvement. Produced by `trace.py::step`, called from `agent.py::run_agent`.
The MCP call is step 2.

```
[1] parse_query
      in:  jeans size 30 under $45
      out: dict with keys: description, size, max_price
      →    regex for size and price, stopword strip for the description
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 1 items: Vintage Levi's 501 Jeans — Medium Wash
      →    1 match(es)
[3] select_item
      in:  1 candidates, taking the best-scored
      out: Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
      →    written to session['selected_item']
[4] suggest_outfit
      in:  Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
      →    ModelUnavailable — stopping, search result kept

  Found "Vintage Levi's 501 Jeans — Medium Wash" but couldn't reach the model
  to style it, so there's no outfit or caption. The search worked — it's the
  writing step that failed. Check your GEMINI_API_KEY in .env, then run the
  same query again.
  (underlying error: The model rejected your API key. Check GEMINI_API_KEY in
  your .env file, or create a fresh key at aistudio.google.com.)
```

This trace shows the improvement working and the model failure in the same run:
step 2 returns the Levi's that the same query found nothing for before, and
step 4 is the live no-key state of this environment. A complete run would carry
on to `create_fit_card` as step 5.

### The three failure modes

| Failure | How it was triggered | What the user sees | Handler |
|---|---|---|---|
| Empty search | `designer ballgown size XXS under $5` — not a ballgown in the file, and nothing at all under $5 | "Nothing in the listings matches description "designer ballgown", size XXS, under $5. Try raising the price ceiling, dropping the size, or using plainer words…" | the branch in `agent.py::run_agent` |
| Empty wardrobe | `python app.py ask 'denim jacket under $50' --empty-wardrobe` | reaches `suggest_outfit`, which switches to the general-advice prompt instead of naming owned pieces | `tools.py::suggest_outfit`, the `if owned:` split, plus a fixed-sentence fallback so it can never return `""` |
| Model unavailable | not simulated — this environment genuinely has no key | "Found "…" but couldn't reach the model to style it… The search worked — it's the writing step that failed. Check your GEMINI_API_KEY in .env" | `except ModelUnavailable` on both model-calling steps in `run_agent` |

Each message names what broke and what to do next. The model-unavailable
handler deliberately keeps whatever the run had already earned rather than
discarding it: a failed caption still reports the outfit, and a failed outfit
still reports the item that was found, because "we found your jeans but
couldn't write about them" is actionable and "something went wrong" is not.

The empty-wardrobe path is the one I can only partly vouch for. The branch is
taken and the prompt changes, which I can see; whether the advice that comes
back is any good needs the model.

## The Improvement

**What I changed:** `agent.py::_normalise_size`. A bare two-digit size between
24 and 44 is converted to W-form before it reaches `search_listings`, so
"size 30" becomes `"W30"`.

**Why I picked it:** it is the defect diagnosed above — the only genuine bug
the test turned up, and it made seven of forty listings unreachable by the
phrasing a real person would use. One change, in the one stage the diagnosis
named.

**Why that band, and why it is safe here:** below 24 is shoe sizing, which
already worked without help — `"8"` *is* a token of `"US 8"`, so letter and
shoe sizes are untouched by this. Above 44 is not a waist in this data. Dress
sizing would collide with the band, and in a catalogue that used it this rule
would be wrong; this one doesn't — every numeric size in `data/listings.json`
is either a US shoe size (7 to 9) or a W-waist (27 to 32), with nothing in
between. That is a fact about this dataset and I have written it into the
function's docstring rather than leaving it as a silent assumption.

### Run Log — After

`python check_criteria.py --label after` →
[`results/criteria_2026-10-19_0139_after.md`](results/criteria_2026-10-19_0139_after.md)
· raw: [`results/run_2026-10-19_0140_after.md`](results/run_2026-10-19_0140_after.md)

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | n/m | n/m | n/m | n/m | n/m | NOT TESTED |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The selected item is the one `suggest_outfit` receives | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is ≤200 chars and mentions the price | 4 of 5 | n/m | n/m | n/m | n/m | n/m | NOT TESTED |
| 5. The price ceiling is respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help?**

**It fixed the bug it was aimed at, and it moved no criterion — and the second
half of that is a fact about my criteria, not about the change.**

The five rows are identical before and after. They were always going to be: the
three measurable ones were already at 5 of 5 with no headroom, and not one of
the five asks anything about size parsing. A run log that cannot distinguish a
system with a whole unreachable product category from one without it is not
measuring the thing that was wrong.

Where it did show, measured directly on the defect:

| Query | Before | After |
|---|---|---|
| `jeans size 30 under $45` | 0 results | 1 — Vintage Levi's 501 Jeans |
| `size 28 corduroy pants` | 0 results | 1 — Corduroy Wide-Leg Pants |
| `straight leg trousers size 30` | 0 results | 1 — Straight Leg Khaki Trousers |
| `cargo pants size 29` | 0 results | 1 — Low-Rise Cargo Pants |
| `carpenter jeans size 32` | 0 results | 1 — Baggy Carpenter Jeans |
| `denim shorts size 27` | 0 results | 1 — High-Waisted Denim Shorts |
| 3 shoe-size queries | unchanged | unchanged |
| 4 letter-size queries | unchanged | unchanged |

Six queries that found nothing now find the right item; nothing that worked
before changed. Criterion 2 still passes 5 of 5, which is the regression I was
most concerned about — a size fix that made fewer searches come back empty
could plausibly have stopped the branch firing, and it didn't.

## What's Still Broken

**Criteria 1 and 4 are untested.** This is the biggest gap and it is not effort.
Both need a live model call and there is no `GEMINI_API_KEY` here. What I would
do: add the key and run `python run_eval.py --label before` and
`python check_criteria.py --label before` again — the scenarios and the scoring
are written and committed, so it is two commands rather than more work. I
stopped here because the alternative was to guess two rows, and a guessed row
in a run log is worse than an empty one.

Of the two, I expect **criterion 4** to be the one that fails. The ≤200
characters is requested in the prompt and enforced nowhere in code, the prompt
asks for the item, the price and the platform all mentioned once each, and
`TEMPERATURE` is 0.9. Asking a model at that temperature for three required
facts inside a hard character budget is the kind of instruction that gets
dropped one element at a time.

**The stopword list leaks.** `"tee under 30 dollars"` parses to a description
of `"tee dollars"`, because "dollars" is not in `_STOPWORDS`. It costs a point
of keyword score to any listing that happens to contain the word. It is a
one-line fix and I did not make it, because the unit allows one change and I
had spent it on the size bug, which actually made items unreachable where this
one only adds noise.

**The description is matched by keyword only.** `"size L sweater under $35"`
returns nothing although there are eight L-ish items under $35, because no
listing title uses the word "sweater" — they are hoodies, blazers and shackets.
That is the "outerwear won't find jacket" limitation I wrote into the MCP tool
description, and it is honest there, but a user hits it without warning. A
synonym map or a semantic match would fix it, and both are larger than one
change.

**The agent always takes the first result.** `search_listings` returns up to
ten and `run_agent` uses `[0]`. For `"denim jacket under $50"` that is right,
but the other six results include denim *shorts* and a denim *vest* — they
score on "denim" alone. The selection step has no notion of whether the match
is the right kind of garment. No criterion tests it, which is consistent with
the pattern above: my criteria watch the tools, and the mistakes are in the
translation around them.

## How I Used AI — unit 4

**Moment 3 — it wrote a monkeypatch that would have reported a false pass.**
Criterion 3 needs the `new_item` that `suggest_outfit` actually receives, so I
asked for instrumentation to capture it. What came back patched
`tools.suggest_outfit`. That looks right and records nothing: `agent.py` does
`from tools import suggest_outfit`, so it holds its own reference, and the
patched name is never the one the loop calls. The `seen` list would have stayed
empty — and because my first version treated an empty list as "nothing to
compare", criterion 3 would have come out FAIL five times for a reason that had
nothing to do with the agent. I moved the wrap onto `agent.suggest_outfit` and
wrote the reason into `check_criteria.py::_recording`. Worth noting that the
failure mode here was a false *negative*; the same mistake in a check written
the other way round is a false pass, which nobody goes looking for.

**Moment 4 — I asked it to argue against my own verdicts.** With three criteria
at 5 of 5 and nothing to diagnose, the comfortable write-up was "the agent
works". I asked for the strongest case that these verdicts were not worth much.
The answer was the one in Verdicts above and I had already written the evidence
for it myself, in unit 3: all three measurable criteria describe paths with no
model in them, in my own words, as the *justification* for a 5-of-5 target. The
argument did not tell me anything the repo didn't already contain — it made me
re-read what I'd written as a claim about the criteria rather than about the
code. That reframing is what sent me to probe the parser, which is where the
actual bug was.
