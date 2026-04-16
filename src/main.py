"""Command line runner for the music recommender simulation."""

from src.recommender import load_songs, recommend_songs


def print_recommendations(title: str, user_prefs: dict, songs: list) -> None:
    """Print the top 5 recommendations for a given user_prefs dict."""
    print(f"\n=== {title} ===")
    print(f"profile: {user_prefs}\n")
    for song, score, explanation in recommend_songs(user_prefs, songs, k=5):
        print(f"  {song['title']} - {song['artist']}  [score {score:.2f}]")
        print(f"    because: {explanation}")


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    default_user = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
    }

    print_recommendations("Default profile (pop / happy / 0.8)", default_user, songs)


if __name__ == "__main__":
    main()
