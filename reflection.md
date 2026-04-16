# Reflection

I ran the recommender with 4 profiles: High-Energy Pop, Chill Lofi, Deep
Intense Rock, and a weird Adversarial one (pop + sad + high energy + wants
acoustic) designed to confuse it.

## How the profiles compared

**Pop vs Lofi.** Opposites on energy and acousticness, and the outputs are
completely different. No overlap. Energy is clearly doing real work in the
ranking.

**Pop vs Rock.** Both high energy, but the top song is different (Sunrise
City vs Storm Runner). They share Gym Hero at rank 2 for rock though, since
it's pop/intense/0.93 — mood and energy good enough to cross over.

**Pop vs Adversarial.** Same genre, same energy, but I asked for sad +
acoustic on the adversarial. It still gave me two happy/intense pop songs
at the top. That was the most annoying result, but honestly expected given
my weights.

**Lofi vs Rock.** Clean separation again.

**Lofi vs Adversarial.** Both want acoustic. Lofi got mostly acoustic
results, adversarial got one acoustic song and the rest were pop. Same
preference, different outcome, because genre and energy buried it.

**Rock vs Adversarial.** Rock got what it asked for. Adversarial did not.

## Experiment: energy x2, genre x0.5

Not as dramatic as I expected. Top 1 usually didn't move. But some songs
shifted ranks — Spacewalk Thoughts (ambient) jumped up for the Lofi profile,
showing that weaker genre weighting lets neighboring genres sneak in.

Weird side effect: the adversarial profile got *worse*. Quiet Porch (the
only sad song) fell out of the top 5 because its energy gap to 0.9 hurt
more with energy weighted higher. So making one kind of bias better made
another worse.

## What surprised me

1. Gym Hero shows up for almost every high-energy profile. It's the catalog
   generalist.
2. The adversarial profile proved the system ignores what you actually want
   if your genre matches. You asked for sad, you got happy. That's the
   model card's main bias story.
3. Halving genre weight didn't blow up the ranking like I thought it would.
   Most of the time, songs that match on genre also match on other things,
   so the genre weight is mostly agreeing with decisions already being made.
