"""Command line runner for the music recommender simulation."""

from src import recommender
from src.recommender import load_songs, recommend_songs


PROFILES = {
    "High-Energy Pop": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.9,
        "likes_acoustic": False,
    },
    "Chill Lofi": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.3,
        "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.95,
        "likes_acoustic": False,
    },
    # adversarial: pop is never sad in this catalog, and high energy fights
    # the low-energy songs that actually do have sad mood. plus likes_acoustic
    # is on but most pop is not acoustic. basically a profile designed to
    # break ties in ugly ways.
    "Adversarial (pop/sad/0.9/acoustic)": {
        "genre": "pop",
        "mood": "sad",
        "energy": 0.9,
        "likes_acoustic": True,
    },
}


def print_recommendations(title: str, user_prefs: dict, songs: list) -> None:
    """Print the top 5 recommendations for a given user_prefs dict."""
    print(f"\n--- {title} ---")
    print(f"profile: {user_prefs}")
    for song, score, explanation in recommend_songs(user_prefs, songs, k=5):
        print(f"  {song['title']} - {song['artist']}  [score {score:.2f}]")
        print(f"    because: {explanation}")


def run_all_profiles(songs: list) -> None:
    for name, prefs in PROFILES.items():
        print_recommendations(name, prefs, songs)


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    print("\n########## DEFAULT WEIGHTS ##########")
    print(f"(genre {recommender.GENRE_POINTS}, mood {recommender.MOOD_POINTS}, "
          f"energy_max {recommender.ENERGY_POINTS_MAX})")
    run_all_profiles(songs)

    # Experiment: double energy, halve genre. Does the system become less
    # obsessed with genre lock-in?
    original_genre = recommender.GENRE_POINTS
    original_energy = recommender.ENERGY_POINTS_MAX
    recommender.GENRE_POINTS = original_genre * 0.5
    recommender.ENERGY_POINTS_MAX = original_energy * 2

    print("\n\n########## EXPERIMENT: energy x2, genre x0.5 ##########")
    print(f"(genre {recommender.GENRE_POINTS}, mood {recommender.MOOD_POINTS}, "
          f"energy_max {recommender.ENERGY_POINTS_MAX})")
    run_all_profiles(songs)

    recommender.GENRE_POINTS = original_genre
    recommender.ENERGY_POINTS_MAX = original_energy


if __name__ == "__main__":
    main()
