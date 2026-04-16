# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

VibeFinder 1.0

---

## 2. Intended Use

Classroom project. Suggests 5 songs from a small catalog (18 songs) based on
a stated favorite genre, mood, target energy, and whether the user wants
acoustic music.

It assumes the user knows what they want and can name it in those four
categories. It is not for real users. It has no personalization, no learning,
no listening history.

---

## 3. How the Model Works

For every song, the system adds up points. Matching genre is worth the
most (2 points). Matching mood is worth less (1 point). Being close to the
user's target energy level is worth a variable amount — closest = max
reward, furthest = zero. Acoustic songs get a small bonus if the user likes
acoustic, a small penalty if they don't.

Once every song has a score, the system sorts them and hands back the top
5, each with a little note saying what rules fired and how many points
they earned.

The starter code had empty function bodies. I wrote all the scoring, the
CSV loading, the ranking, and a shared helper so the OOP and functional
paths use the same math.

---

## 4. Data

18 songs in `data/songs.csv`. The starter gave me 10, I added 8.

Genres covered: pop, lofi, rock, ambient, jazz, synthwave, indie pop,
hip hop, country, folk, electronic, r&b, metal, classical, indie rock.

Moods covered: happy, chill, intense, relaxed, focused, moody, energetic,
nostalgic, sad, romantic, melancholy.

Skew I noticed: pop and lofi are overrepresented. Only one sad song exists
in the whole catalog. No latin, no k-pop, no gospel. The taste this dataset
represents is basically mine — I picked what felt like a reasonable spread,
but "reasonable to me" isn't neutral.

---

## 5. Strengths

- Works well for "clean" profiles where genre, mood, and energy all point
  the same direction. Pop-happy-high-energy, lofi-chill-low-energy, and
  rock-intense-high-energy all returned the song I would have picked by hand.
- Every recommendation comes with a reasons list, so you can see exactly
  why a song ranked where it did. That transparency is underrated.
- Easy to tune. The weights are five named constants at the top of
  `recommender.py`. Changing behavior is a one-line edit.
- Deterministic. Same profile always returns the same result, which made
  comparing the experiment runs straightforward.

---

## 6. Limitations and Bias

The biggest problem: the system ignores what the user explicitly asked for
if the genre happens to match. My adversarial profile asked for "pop + sad +
high energy + acoustic." The top two results were pop, happy, and not
acoustic at all. Genre + energy together were worth more points than mood +
acoustic bonus, so the system gave the user an answer that technically scored
high but totally missed the request.

Other limitations I saw:

- **Genre lock-in.** If you pick "pop," you almost never see rock or lofi
  in your top 5 even if they'd match on every other feature.
- **String equality is too strict.** "indie pop" earns zero genre points
  from a "pop" user, and "relaxed" earns nothing from a "chill" user, even
  though those are effectively neighbors.
- **Catalog skew.** Pop and lofi are overrepresented in 18 songs. Users of
  underrepresented genres (metal, classical) get less variety and lower
  top scores.
- **No diversity in results.** Two very similar lofi songs (Library Rain
  and Midnight Coding) both sit at the top for the Chill Lofi profile.
  Nothing encourages variety.

---

## 7. Evaluation

I tested with four profiles: High-Energy Pop, Chill Lofi, Deep Intense Rock,
and an Adversarial profile designed to break it (pop + sad + high energy +
acoustic, where pop is never sad in my catalog).

For each profile I looked at whether the top result "felt right" given the
preferences, and whether the full top-5 made sense. Then I ran a weight
experiment (energy x2, genre x0.5) to test sensitivity.

What I found:

- The three "normal" profiles all got sensible top-1 results that matched
  what a human would pick.
- The adversarial profile gave pop/happy songs instead of the sad/acoustic
  ones the user asked for, which is the biggest failure mode.
- The weight experiment moved mid-ranks around but usually kept the top-1,
  suggesting genre and energy reinforce each other more than I thought.
- There's a pytest suite (`tests/test_recommender.py`) covering the OOP
  path — sorting by score and non-empty explanation strings.

Full details in `reflection.md`.

---

## 8. Future Work

- Partial genre matching. "indie pop" should get something from a "pop"
  user, not zero.
- Soft mood clusters. "chill," "relaxed," and "focused" should be treated
  as neighbors.
- Diversity penalty so the top 5 isn't dominated by near-duplicate lofi
  tracks from the same artist.
- Bigger and more balanced catalog before drawing any conclusions.

---

## 9. Personal Reflection

The biggest learning moment was running the adversarial profile and watching
the system hand me pop-happy songs when I asked for sad-acoustic. Nothing
was broken, the math was working exactly as I wrote it, but the output was
wrong in a way that matched the kind of complaint people have about real
recommenders. It made the "filter bubble" idea feel concrete instead of
abstract.

AI tools were helpful for boilerplate (CSV loading, Mermaid syntax, docstring
cleanup) but I had to push back when suggestions wanted to make the scoring
fancier than it needed to be. Keeping the weights simple was the whole
point — if I can't reason about the output, I can't debug the bias.

What surprised me most was how "smart" a dumb algorithm can feel just by
showing its work. Attaching reasons to every recommendation made a pile of
addition feel like it was explaining itself. Real apps do the same trick,
and it's easier to trust them than they probably deserve.

If I extended this I'd add fuzzy genre/mood matching, a diversity term, and
try actual collaborative filtering on a bigger dataset. The current
bottleneck is the catalog, not the algorithm.
