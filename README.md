# Music Recommender Simulation

## Project Summary

This is a tiny content-based music recommender. You give it a "taste profile"
(your favorite genre, mood, target energy, whether you like acoustic stuff) and
it scores every song in a small CSV catalog, then returns the top matches with
a short list of reasons for each pick.

The point isn't to compete with Spotify. The point is to get a feel for how a
real recommender turns user data + item data into a ranked list, and to be
honest about where this kind of system breaks.

---

## How The System Works

### What real platforms do (the short version)

Big platforms like Spotify and YouTube Music don't use one algorithm, they use
a stack of them. Two of the main ideas:

- **Collaborative filtering** looks at *other people*. If a lot of users who
  liked the songs you liked also liked some other song, that other song gets
  recommended to you. It doesn't really care what the song *sounds* like, it
  just cares about overlapping behavior. Likes, skips, completion rates,
  playlist co-occurrence, all of that feeds in.
- **Content-based filtering** looks at *the songs themselves*. Each song gets
  described by features (genre, tempo, energy, mood, audio fingerprints, etc),
  and the system recommends songs whose features look like the ones you already
  enjoy. No other users required.

In practice the big apps blend both, plus a bunch of deep learning models that
predict things like "will this user finish this track" or "will this user save
this." Skips count more than you'd think.

### What my version does

My version is purely content-based, because that's the part you can actually
build and reason about in a few hours. It does:

1. Loads a small CSV of songs, where each song has descriptive features.
2. Takes a `UserProfile` describing what the listener wants.
3. Scores every song against the profile using a simple weighted rule.
4. Sorts by score and returns the top `k` results, each with a list of reasons
   like "genre match (+2.0)" so you can see why it picked them.

There's no learning happening. The weights are written by me, by hand. That's
on purpose, it makes the behavior easy to inspect and easy to break in
interesting ways for the bias section.

### Features used

`Song` (one row in `data/songs.csv`):

- `id`, `title`, `artist` — identity, not used for scoring
- `genre` — categorical (pop, lofi, rock, etc)
- `mood` — categorical (happy, chill, intense, etc)
- `energy` — float 0.0–1.0
- `tempo_bpm` — beats per minute
- `valence` — float 0.0–1.0, roughly "musical positivity"
- `danceability` — float 0.0–1.0
- `acousticness` — float 0.0–1.0

`UserProfile`:

- `favorite_genre` — string, exact-match against the song's genre
- `favorite_mood` — string, exact-match against the song's mood
- `target_energy` — float 0.0–1.0, the user's preferred energy level
- `likes_acoustic` — bool, whether to give a small bonus to acoustic tracks

The exact scoring weights and the full recipe live in the next section, after
Phase 2.

---

## Algorithm Recipe

*(filled in during Phase 2)*

---

## Getting Started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python -m src.main
```

### Tests

```bash
pytest
```

---

## Experiments

*(filled in during Phase 4)*

---

## Limitations and Risks

*(short version here, full discussion in `model_card.md`)*

---

## Reflection

*(filled in during Phase 5, see also `model_card.md` and `reflection.md`)*
