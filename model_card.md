# Model Card: VibeFinder Applied AI Music Advisor

## 1. System Name

VibeFinder 2.0 — Applied AI Music Advisor.

Built on top of my Module 3 starter
`ai110-module3show-musicrecommendersimulation-starter`, which
already had a working content-based recommender. VibeFinder adds the
parser, retriever, agent loop, evaluator, logging, and reliability
harness around it.

---

## 2. Intended Use

A homework / portfolio demo of an applied AI system: take a
plain-English music request, hand back a ranked song list with a
confidence score, an evidence list, and warnings when the request
can't be honestly satisfied by the catalog.

It is meant for inspection, demonstration, and grading. It is not
meant to actually recommend music to real users.

---

## 3. Not Intended Use

- Production recommendation. Catalog is 18 songs and the parser is
  a keyword scanner.
- Anything where confidence numbers might be quoted as if they
  meant calibrated probability. The score is a weighted rubric, not
  a probability.
- Sensitive contexts (mental-health prompts, medical advice
  hidden in a "sad music" request, etc). The system will happily
  return a folk song if you say "sad," and that is the only thing
  it will do.

---

## 4. How It Works

A single user request flows through five components:

1. **`profile_parser.py`** — keyword + rule matching. Maps activity
   words ("coding," "gym"), mood words, energy phrases, and an
   acoustic/electronic flag onto a structured `ParsedProfile`.
   Conflicts (multiple genres, sad-with-high-energy, acoustic vs
   electronic) are recorded as warnings instead of overwriting each
   other silently.
2. **`retriever.py`** — strict pass keeps any song with two or more
   pieces of evidence (genre match, mood match, energy within 0.20,
   acoustic match). Evidence is attached to each candidate so the
   agent and evaluator can see it.
3. **`recommender.py`** — original Module 3 weighted scorer. Same
   constants, same explanation strings. The agent calls into this
   through `score_song`.
4. **`evaluator.py`** — hand-written rubric: weighted average of
   genre ratio, mood ratio, energy closeness, acoustic match, and
   coverage. Produces a `confidence` in `[0, 1]`, a
   `passed_guardrails` boolean, and a list of warnings.
5. **`advisor_agent.py`** — orchestrates the loop, writes JSONL
   events to `logs/run_log.jsonl`, and retries once with the
   relaxed retrieval mode (genre/mood neighbors, wider energy
   tolerance) if confidence is below 0.55. The relaxed result is
   only adopted if it actually improved confidence.

---

## 5. Data

`data/songs.csv`. 18 rows. Each song has: id, title, artist, genre,
mood, energy, tempo_bpm, valence, danceability, acousticness.

Genres covered: pop, lofi, rock, ambient, jazz, synthwave, indie pop,
hip hop, country, folk, electronic, r&b, metal, classical, indie
rock.

Moods covered: happy, chill, intense, relaxed, focused, moody,
energetic, nostalgic, sad, romantic, melancholy.

Skew (carried from the Module 3 model card and still true): pop and
lofi are over-represented. Only one truly sad song. No latin, no
k-pop, no gospel. The set reflects my own taste, not a balanced
sample.

---

## 6. Strengths

- Deterministic and inspectable. Same input always returns the same
  output. Every weight, threshold, and neighbor table is named in
  source.
- Explanations attached at every layer. Each candidate carries an
  evidence list, each recommendation carries a `because` string,
  and each evaluation carries a metrics dict.
- Honest about its own limits. Confidence below threshold triggers
  retry; sparse or contradictory requests come back with warnings;
  the harness reports failures rather than smoothing them over.
- Test harness exercises the live agent rather than mocked stubs.
  All 7 reliability cases hit `data/songs.csv` through the real
  pipeline.

---

## 7. Limitations and Bias

- **Keyword scanner blindness.** "Anything but pop" still triggers
  pop. Negation, sarcasm, and idiom are completely lost.
- **Catalog skew.** Pop and lofi over-represented; users of
  under-represented genres get less variety and lower confidence
  scores.
- **Hand-picked weights.** Genre 0.30, mood 0.25, energy 0.25,
  acoustic 0.10, coverage 0.10. Defensible, but reflect my
  judgment, not a learned signal.
- **Hand-picked neighbor tables.** "indie pop" is a neighbor of
  "pop" because I said so. Different people would draw the
  neighborhoods differently.
- **String-equality genre/mood matching at the ranker level.** The
  retriever softens this with neighbor tables, but the original
  scoring rule is still strict-equality, so the ranker rewards
  exact matches more than feels right at the catalog scale.
- **No diversity term.** Two near-duplicate lofi tracks from the
  same artist can both sit in the top 5 for a calm-coding profile.

---

## 8. Reliability Testing

Two layers:

- **`pytest` suite** — `tests/test_profile_parser.py`,
  `test_retriever.py`, `test_evaluator.py`, `test_advisor_agent.py`,
  and the original `test_recommender.py`. Covers parser keyword
  behavior, contradiction warnings, empty/garbage input, retriever
  evidence and relaxed mode, evaluator unit-interval and
  guardrails, and the end-to-end agent path including JSONL
  logging. Most recent run: 20 passed.
- **`src/evaluate.py` reliability harness** — 7 cases that drive
  the live agent against the real catalog and check parsed
  profile, confidence band, and expected warnings. Most recent
  run: 7 / 7 passing, average confidence 0.677.

Confidence rubric weights and the `CONFIDENCE_PASS = 0.55`
threshold are exposed as constants in `src/evaluator.py`. Anyone
auditing the system can change them and rerun the harness.

---

## 9. Misuse Risks and Prevention

- **Misleading authority of confidence numbers.** "Confidence 0.84"
  sounds calibrated and isn't. Mitigation: the README and this
  card both say it's a hand-written rubric, not a probability, and
  the metrics dict shows the underlying ratios so a reader can see
  what fed the number.
- **Silent steering by weight changes.** Whoever tunes the weights
  shapes the output. Mitigation: the constants are at the top of
  `evaluator.py` / `recommender.py` and not buried; the harness
  re-runs against them so any change is visible immediately.
- **"It told me to" risk.** A user could read a sad-music
  recommendation as advice. Mitigation: this is documented as
  out-of-scope in section 3, and contradictory or thin requests
  come back with explicit warnings rather than confident answers.

---

## 10. What Surprised Me During Testing

The thing that genuinely caught me out was that the relaxed retry
sometimes made the result *worse* on confidence. Not by a lot, but
enough that I had to add the "only adopt the retry if it improved
confidence" check. Without it, a request that the strict pass had
answered cleanly could end up with a wider, weaker result just
because confidence had been near the threshold. That was a
behavioral bug I would not have spotted without the harness — the
unit tests said everything was fine, the harness said the average
confidence dropped.

The other surprise was how much the parser quality drove the
evaluator's output. I kept thinking confidence would be limited by
the catalog, but for the most part the catalog was fine — what
moved the score up or down was whether the parser had the right
mood and energy band. The "sad with no explicit energy" failure I
caught in the harness is a great example: adding a single
mood-defaults table moved that case from FAIL to PASS without
touching the catalog at all.

---

## 11. AI Collaboration Reflection

I worked with Claude as my coding partner on this project, in much
the same way I'd work with a senior dev who has loaded the
assignment.

**A helpful suggestion.** When I was sketching the agent loop,
Claude suggested making the relaxed-retry conditional on actually
improving confidence — not just running it whenever the strict
pass scored low. That ended up catching the bug above where the
relaxed pass returned a wider but weaker set. I would have written
"retry on low confidence, replace result" and shipped it without
the check.

**A flawed suggestion.** Earlier in the build, I asked for an
energy-from-mood default and the first version it produced
overrode explicit energy phrases. So if the user said "sad music,
high energy" the parser would still snap energy down to 0.30
because "sad" mapped to it. That hid the contradiction the
adversarial case is supposed to expose. I had to push back and
make the rule "mood default applies *only* when no explicit
energy phrase was matched." After that change, the
contradictory-sad-high-energy case correctly produced both the
high energy reading and the low-arousal warning.

The takeaway is the same as Module 3: AI tools are great at
boilerplate and at suggesting structures I hadn't thought of, but
they will happily write convenient logic that erases the very
behavior the assignment is supposed to test. The harness is what
keeps me honest, not the AI.

---

## 12. Future Work

- Replace string-equality genre/mood matching in the ranker with
  the same neighbor tables retrieval already uses, so partial
  matches earn partial points end-to-end.
- Diversity penalty in the ranker so the top 5 isn't dominated by
  near-duplicates.
- Bigger, more balanced catalog before drawing any conclusion
  about whether the rubric weights are reasonable.
- A genuinely small local LLM on the parser side, kept behind a
  flag, so the rule-based parser stays the audited fallback.
