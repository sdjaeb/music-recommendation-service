import json
import random
import os
import csv
from datetime import datetime, timedelta

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm library not found. Please install it with 'pip install tqdm'")
    # Provide a dummy tqdm class if the library is not installed
    class tqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
            self.total = kwargs.get('total', len(iterable) if iterable else 0)
            self.n = 0

        def __iter__(self):
            for obj in self.iterable:
                yield obj
                self.update(1)

        def update(self, n=1):
            self.n += n
            # Simple text-based progress
            print(f"\rProgress: {self.n}/{self.total}", end="")
            if self.n == self.total:
                print()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

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
ARTISTS = [{"id": i, "name": f"Artist {i}"} for i in range(1, 501)]

OUTPUT_DIR = "generated_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_current_count(day_index, start_count, final_count):
    """Calculates the current number of users or songs based on linear growth."""
    return int(start_count + (final_count - start_count) * (day_index / TOTAL_DAYS))

# --- 1. Generate Dimension Data ---
print("Generating dimension data...")

# Songs
songs = []
for i in range(1, FINAL_SONGS + 1):
    release_day = random.randint(0, TOTAL_DAYS)
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
users = []
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

# --- 2. Define Popularity Modifiers ---
sleeper_hits = {s['track_id']: (START_DATE + timedelta(days=random.randint(90, 300))) for s in random.sample(songs, 20)}
genre_events = {
    "Rock": (datetime(2024, 3, 15), datetime(2024, 4, 15)),
    "Electronic": (datetime(2024, 7, 1), datetime(2024, 7, 31)),
}

# --- 3. Generate Fact Data (Listening History) ---
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
        active_song_count = get_current_count(day_index, START_SONGS, FINAL_SONGS)
        active_users = [u for u in users if datetime.strptime(u['join_date'], '%Y-%m-%d') <= current_date]
        active_songs = [s for s in songs if datetime.strptime(s['release_date'], '%Y-%m-%d') <= current_date]

        if not active_users or not active_songs:
            continue

        # Calculate song weights for this day
        song_weights = []
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
                possible_songs_with_weights = [(s, w) for s, w in zip(active_songs, song_weights) if s['genre'] == genre]
                if not possible_songs_with_weights:
                    possible_songs_with_weights = list(zip(active_songs, song_weights))
            else:
                possible_songs_with_weights = list(zip(active_songs, song_weights))
            
            songs_to_choose, weights_to_choose = zip(*possible_songs_with_weights)
            chosen_song = random.choices(songs_to_choose, weights=weights_to_choose, k=1)[0]

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