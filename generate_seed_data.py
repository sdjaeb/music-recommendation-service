import random
import os
import csv
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
END_DATE = datetime(2024, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

START_USERS = 200
FINAL_USERS = 500
START_SONGS = 10000
FINAL_SONGS = 30000

EVENTS_PER_DAY_AVG = 15000

GENRES = ["Pop", "Rock", "Hip-Hop", "Jazz", "Electronic", "Classical", "Country"]
ARTISTS: List[Dict[str, Any]] = [{"id": i, "name": f"Artist {i}"} for i in range(1, 501)]

OUTPUT_DIR = "generated_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_current_count(day_index: int, start_count: int, final_count: int) -> int:
    """Calculates the current number of users or songs based on linear growth."""
    return int(start_count + (final_count - start_count) * (day_index / TOTAL_DAYS))

# --- 1. Generate Dimension Data ---
print("Generating dimension data...")

# Songs
songs: List[Dict[str, Any]] = []
for i in range(1, FINAL_SONGS + 1):
    release_day: int = random.randint(0, TOTAL_DAYS)
    artist = random.choice(ARTISTS)
    songs.append({
        "track_id": 10000 + i,
        "title": f"Song Title {i}",
        "artist_id": artist["id"],
        "artist_name": artist["name"],
        "genre": random.choice(GENRES),
        "duration_ms": random.randint(120000, 300000),
        "release_date": (START_DATE + timedelta(days=release_day)).strftime('%Y-%m-%d'),
        "base_popularity": random.uniform(0.1, 1.0)
    })

with open(os.path.join(OUTPUT_DIR, "dim_songs.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=songs[0].keys())
    writer.writeheader()
    writer.writerows(songs)
print(f"Generated {len(songs)} songs in dim_songs.csv")

# Users
users: List[Dict[str, Any]] = []
for i in range(1, FINAL_USERS + 1):
    join_day = random.randint(0, TOTAL_DAYS)
    users.append({
        "user_id": i,
        "user_name": f"User_{i}",
        "preferred_genres": ",".join(random.sample(GENRES, random.randint(1, 3))),
        "join_date": (START_DATE + timedelta(days=join_day)).strftime('%Y-%m-%d')
    })

with open(os.path.join(OUTPUT_DIR, "dim_users.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=users[0].keys())
    writer.writeheader()
    writer.writerows(users)
print(f"Generated {len(users)} users in dim_users.csv")

# --- 2. Generate Relationship Data ---
print("Generating relationship data (follows, playlists)...")

# User Follows Graph
follows: Set[Tuple[int, int]] = set()
for user in users:
    # Each user follows between 5 and 20 other users
    num_to_follow = random.randint(5, 20)
    
    # Exclude the user themselves from the potential follow list
    potential_follows = [u for u in users if u['user_id'] != user['user_id']]
    
    # If there are enough users to follow
    if len(potential_follows) >= num_to_follow:
        followed_users = random.sample(potential_follows, num_to_follow)
        for followed_user in followed_users:
            # Store in a canonical order to handle two-way follows and prevent duplicates
            user_a = min(user['user_id'], followed_user['user_id'])
            user_b = max(user['user_id'], followed_user['user_id'])
            follows.add((user_a, user_b))

# Write the two-way follow graph
with open(os.path.join(OUTPUT_DIR, "graph_user_follows.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["user_id_a", "user_id_b"])
    follow_count = 0
    for user_a, user_b in follows:
        writer.writerow([user_a, user_b])
        writer.writerow([user_b, user_a])
        follow_count += 2
print(f"Generated {follow_count} follow relationships in graph_user_follows.csv")

# Playlists and Playlist Tracks
playlists: List[Dict[str, Any]] = []
playlist_tracks: List[Dict[str, int]] = []
playlist_id_counter: int = 1

for user in tqdm(users, desc="Generating playlists"):
    # Each user creates between 0 and 5 playlists
    num_playlists = random.randint(0, 5)
    user_join_date = datetime.strptime(user['join_date'], '%Y-%m-%d')
    
    for _ in range(num_playlists):
        playlist_created_day = random.randint((user_join_date - START_DATE).days, TOTAL_DAYS)
        playlist_created_date = START_DATE + timedelta(days=playlist_created_day)
        
        playlists.append({
            "playlist_id": playlist_id_counter,
            "playlist_name": f"{user['user_name']}'s Mix #{_+1}",
            "owner_user_id": user['user_id'],
            "created_date": playlist_created_date.strftime('%Y-%m-%d')
        })
        
        # Add tracks to this playlist
        num_tracks_in_playlist = random.randint(10, 50)
        available_songs = [s for s in songs if datetime.strptime(s['release_date'], '%Y-%m-%d') <= playlist_created_date]
        if not available_songs: continue

        songs_for_playlist = random.sample(available_songs, min(len(available_songs), num_tracks_in_playlist))
            
        for song in songs_for_playlist:
            playlist_tracks.append({ "playlist_id": playlist_id_counter, "track_id": song['track_id'] })
            
        playlist_id_counter += 1

if playlists:
    with open(os.path.join(OUTPUT_DIR, "dim_playlists.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=playlists[0].keys())
        writer.writeheader()
        writer.writerows(playlists)
    print(f"Generated {len(playlists)} playlists in dim_playlists.csv")

if playlist_tracks:
    with open(os.path.join(OUTPUT_DIR, "bridge_playlist_tracks.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=playlist_tracks[0].keys())
        writer.writeheader()
        writer.writerows(playlist_tracks)
    print(f"Generated {len(playlist_tracks)} playlist-track relationships in bridge_playlist_tracks.csv")

# --- 3. Define Popularity Modifiers ---
sleeper_hits: Dict[int, datetime] = {s['track_id']: (START_DATE + timedelta(days=random.randint(90, 300))) for s in random.sample(songs, 20)}
genre_events: Dict[str, Tuple[datetime, datetime]] = {
    "Rock": (datetime(2024, 3, 15), datetime(2024, 4, 15)),
    "Electronic": (datetime(2024, 7, 1), datetime(2024, 7, 31)),
}

# --- 4. Generate Fact Data (Listening History) ---
print("Generating historical listening events for 2024...")
event_count = 0
fact_file_path = os.path.join(OUTPUT_DIR, "fact_listening_events_2024.csv")
with open(fact_file_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["event_id", "user_id", "track_id", "event_type", "timestamp"])

    for day_index in tqdm(range(TOTAL_DAYS + 1), desc="Generating daily events"):
        current_date = START_DATE + timedelta(days=day_index)
        
        # Determine active users and songs for the day
        active_user_count = get_current_count(day_index, START_USERS, FINAL_USERS)
        active_song_count = get_current_count(day_index, START_SONGS, FINAL_SONGS) # This line is not used, but kept for context
        active_users: List[Dict[str, Any]] = [u for u in users if datetime.strptime(u['join_date'], '%Y-%m-%d') <= current_date]
        active_songs: List[Dict[str, Any]] = [s for s in songs if datetime.strptime(s['release_date'], '%Y-%m-%d') <= current_date]

        if not active_users or not active_songs:
            continue

        # Calculate song weights for this day
        song_weights: List[float] = []
        for song in active_songs:
            weight = song['base_popularity']
            # Apply sleeper hit modifier
            if song['track_id'] in sleeper_hits and sleeper_hits[song['track_id']] <= current_date:
                weight *= 5.0
            # Apply genre event modifier
            if song['genre'] in genre_events:
                start, end = genre_events[song['genre']]
                if start <= current_date <= end:
                    weight *= 1.5
            song_weights.append(weight)

        # Generate events for the day
        events_today = int(EVENTS_PER_DAY_AVG * (1 + random.uniform(-0.3, 0.3)))
        for i in range(events_today):
            user = random.choice(active_users)
            
            # User is more likely to listen to songs in their preferred genres
            if random.random() < 0.6:
                pref_genres = user['preferred_genres'].split(',')
                genre = random.choice(pref_genres)
                possible_songs_with_weights: List[Tuple[Dict[str, Any], float]] = [(s, w) for s, w in zip(active_songs, song_weights) if s['genre'] == genre]
                if not possible_songs_with_weights:
                    possible_songs_with_weights = list(zip(active_songs, song_weights))
            else:
                possible_songs_with_weights = list(zip(active_songs, song_weights))
            
            songs_to_choose, weights_to_choose = zip(*possible_songs_with_weights)
            chosen_song: Dict[str, Any] = random.choices(songs_to_choose, weights=weights_to_choose, k=1)[0]

            # Simulate different event types
            event_type_roll = random.random()
            event_type = "skip"
            if event_type_roll < 0.7: event_type = "complete_listen"
            elif event_type_roll < 0.85: event_type = "like"

            # Generate a random timestamp within the current day
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