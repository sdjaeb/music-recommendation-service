import random
import os
import csv
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Any

try:
    from tqdm import tqdm
except ImportError:
    print("Error: The 'tqdm' library is required to run this script.")
    print("Please install it using: pip install tqdm (or uv pip install tqdm)")
    sys.exit(1)

print("Starting generation of realistic seed data...")

# --- Configuration ---
START_DATE = datetime(2024, 1, 1)

START_USERS = 200
FINAL_USERS = 500
START_SONGS = 10000
FINAL_SONGS = 30000

EVENTS_PER_DAY_AVG = 15000

GENRES = ["Pop", "Rock", "Hip-Hop", "Jazz", "Electronic", "Classical", "Country"]
ARTISTS: List[Dict[str, Any]] = [{"id": i, "name": f"Artist {i}"} for i in range(1, 501)]

OUTPUT_DIR = "generated_data"

def main(total_days: int):
    """
    Main function to generate all seed data.
    :param total_days: The number of days of data to generate.
    """
    end_date = START_DATE + timedelta(days=total_days - 1)
    print(f"Starting data generation for {total_days} days ({START_DATE.date()} to {end_date.date()})...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 1. Generate Dimension Data ---
    print("Generating dimension data...")

    # Songs
    songs: List[Dict[str, Any]] = []
    for i in range(1, FINAL_SONGS + 1):
        release_day: int = random.randint(0, total_days - 1)
        artist = random.choice(ARTISTS)
        songs.append({
            "track_id": 10000 + i,
            "title": f"Song Title {i}",
            "artist_id": artist["id"],
            "artist_name": artist["name"],
            "genre": random.choice(GENRES),
            "duration_ms": random.randint(120000, 300000),
            "release_date": (START_DATE + timedelta(days=release_day)),
            "base_popularity": random.uniform(0.1, 1.0)
        })

    # Users
    users: List[Dict[str, Any]] = []
    for i in range(1, FINAL_USERS + 1):
        join_day = random.randint(0, total_days - 1)
        users.append({
            "user_id": i,
            "user_name": f"User_{i}",
            "preferred_genres": ",".join(random.sample(GENRES, random.randint(1, 3))),
            "join_date": (START_DATE + timedelta(days=join_day))
        })

    # --- 2. Generate Relationship Data ---
    print("Generating relationship data (follows, playlists)...")

    # User Follows Graph
    follows: Set[Tuple[int, int]] = set()
    for user in users:
        num_to_follow = random.randint(5, 20)
        potential_follows = [u for u in users if u['user_id'] != user['user_id']]
        if len(potential_follows) >= num_to_follow:
            followed_users = random.sample(potential_follows, num_to_follow)
            for followed_user in followed_users:
                user_a = min(user['user_id'], followed_user['user_id'])
                user_b = max(user['user_id'], followed_user['user_id'])
                follows.add((user_a, user_b))

    # Playlists and Playlist Tracks
    playlists: List[Dict[str, Any]] = []
    playlist_tracks: List[Dict[str, int]] = []
    playlist_id_counter: int = 1

    for user in tqdm(users, desc="Generating playlists"):
        num_playlists = random.randint(0, 5)
        user_join_date: datetime = user['join_date']
        
        for _ in range(num_playlists):
            # Ensure playlist is created on or after the user joins
            playlist_created_day = random.randint((user_join_date - START_DATE).days, total_days - 1)
            playlist_created_date = START_DATE + timedelta(days=playlist_created_day)
            
            playlists.append({
                "playlist_id": playlist_id_counter,
                "playlist_name": f"{user['user_name']}'s Mix #{_+1}",
                "owner_user_id": user['user_id'],
                "created_date": playlist_created_date
            })
            
            num_tracks_in_playlist = random.randint(10, 50)
            # Filter for songs released on or before the playlist creation date
            available_songs = [s for s in songs if s['release_date'] <= playlist_created_date]
            if not available_songs: continue

            songs_for_playlist = random.sample(available_songs, min(len(available_songs), num_tracks_in_playlist))
                
            for song in songs_for_playlist:
                playlist_tracks.append({ "playlist_id": playlist_id_counter, "track_id": song['track_id'] })
                
            playlist_id_counter += 1

    # --- 3. Write Dimension and Relationship Data to CSV ---
    print("Writing dimension and relationship data to CSV files...")

    # Helper to format datetimes in rows to strings for CSV writing
    def format_row_dates(row: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v.strftime('%Y-%m-%d') if isinstance(v, datetime) else v for k, v in row.items()}

    with open(os.path.join(OUTPUT_DIR, "dim_songs.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=songs[0].keys())
        writer.writeheader()
        writer.writerows(map(format_row_dates, songs))
    print(f"Generated {len(songs)} songs in dim_songs.csv")

    with open(os.path.join(OUTPUT_DIR, "dim_users.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(map(format_row_dates, users))
    print(f"Generated {len(users)} users in dim_users.csv")

    with open(os.path.join(OUTPUT_DIR, "graph_user_follows.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id_a", "user_id_b"])
        for user_a, user_b in follows:
            writer.writerow([user_a, user_b])
            writer.writerow([user_b, user_a])
    print(f"Generated {len(follows) * 2} follow relationships in graph_user_follows.csv")

    if playlists:
        with open(os.path.join(OUTPUT_DIR, "dim_playlists.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=playlists[0].keys())
            writer.writeheader()
            writer.writerows(map(format_row_dates, playlists))
        print(f"Generated {len(playlists)} playlists in dim_playlists.csv")

    if playlist_tracks:
        with open(os.path.join(OUTPUT_DIR, "bridge_playlist_tracks.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=playlist_tracks[0].keys())
            writer.writeheader()
            writer.writerows(playlist_tracks)
        print(f"Generated {len(playlist_tracks)} playlist-track relationships in bridge_playlist_tracks.csv")

    # --- 4. Define Popularity Modifiers ---
    # For sleeper hits, define a dynamic window based on the total duration.
    # A "sleeper hit" will emerge in the latter 75% of the time period.
    sleeper_hit_min_day = total_days // 4
    sleeper_hit_max_day = total_days - 1

    # Only create sleeper hits if the window is valid and there are enough songs.
    if sleeper_hit_min_day < sleeper_hit_max_day and len(songs) >= 20:
        sleeper_hits: Dict[int, datetime] = {
            s['track_id']: (START_DATE + timedelta(days=random.randint(sleeper_hit_min_day, sleeper_hit_max_day)))
            for s in random.sample(songs, 20)
        }
    else:
        sleeper_hits: Dict[int, datetime] = {}
    genre_events: Dict[str, Tuple[datetime, datetime]] = {
        "Rock": (datetime(2024, 3, 15), datetime(2024, 4, 15)),
        "Electronic": (datetime(2024, 7, 1), datetime(2024, 7, 31)),
    }

    # --- 5. Generate Fact Data (Listening History) ---
    print("Generating historical listening events...")

    # --- Performance Optimization: Pre-sort users and songs by date ---
    # This avoids repeatedly filtering the full list every day.
    songs.sort(key=lambda x: x['release_date'])
    users.sort(key=lambda x: x['join_date'])

    event_count = 0
    fact_file_path = os.path.join(OUTPUT_DIR, "fact_listening_events.csv")

    # Pointers for efficient addition of active users/songs
    next_user_idx = 0
    next_song_idx = 0
    active_users: List[Dict[str, Any]] = []
    active_songs: List[Dict[str, Any]] = []

    with open(fact_file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "user_id", "track_id", "event_type", "timestamp"])

        for day_index in tqdm(range(total_days), desc="Generating daily events"):
            current_date = START_DATE + timedelta(days=day_index)

            # Efficiently add new users who joined today or earlier
            while next_user_idx < len(users) and users[next_user_idx]['join_date'] <= current_date:
                active_users.append(users[next_user_idx])
                next_user_idx += 1

            # Efficiently add new songs released today or earlier
            while next_song_idx < len(songs) and songs[next_song_idx]['release_date'] <= current_date:
                active_songs.append(songs[next_song_idx])
                next_song_idx += 1

            if not active_users or not active_songs:
                continue

            # Calculate song weights for this day based on the current active song pool
            song_weights: List[float] = []
            for song in active_songs:
                weight = song['base_popularity']
                if song['track_id'] in sleeper_hits and sleeper_hits[song['track_id']] <= current_date:
                    weight *= 5.0
                if song['genre'] in genre_events:
                    start, end = genre_events[song['genre']]
                    if start <= current_date <= end:
                        weight *= 1.5
                song_weights.append(weight)

            # Generate events for the day
            events_today = int(EVENTS_PER_DAY_AVG * (1 + random.uniform(-0.3, 0.3)))
            for _ in range(events_today):
                user = random.choice(active_users)

                # User is more likely to listen to songs in their preferred genres
                if random.random() < 0.6:
                    pref_genres = user['preferred_genres'].split(',')
                    genre = random.choice(pref_genres)
                    possible_songs_with_weights = [(s, w) for s, w in zip(active_songs, song_weights) if s['genre'] == genre]
                    if not possible_songs_with_weights:
                        possible_songs_with_weights = list(zip(active_songs, song_weights))
                else:
                    possible_songs_with_weights = list(zip(active_songs, song_weights))

                songs_to_choose, weights_to_choose = zip(*possible_songs_with_weights)
                chosen_song: Dict[str, Any] = random.choices(songs_to_choose, weights=weights_to_choose, k=1)[0]

                event_type_roll = random.random()
                event_type = "skip"
                if event_type_roll < 0.7: event_type = "complete_listen"
                elif event_type_roll < 0.85: event_type = "like"

                event_timestamp = current_date + timedelta(seconds=random.randint(0, 86399))

                writer.writerow([
                    f"evt_{event_count}",
                    user['user_id'],
                    chosen_song['track_id'],
                    event_type,
                    event_timestamp.isoformat() + "Z"
                ])
                event_count += 1

    print(f"Generated {event_count} total events in {fact_file_path}")
    print("\nHistorical data generation complete.")
    print(f"Data saved in '{OUTPUT_DIR}/' directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate realistic seed data for a music service.")
    parser.add_argument(
        "--days",
        type=int,
        default=366, # 2024 is a leap year
        help="Number of days to generate data for. Defaults to 366."
    )
    args = parser.parse_args()

    if args.days <= 0:
        print("Error: --days must be a positive number.", file=sys.stderr)
        sys.exit(1)

    main(args.days)