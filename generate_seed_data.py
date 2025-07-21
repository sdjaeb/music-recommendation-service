import json
import random
import os
import shutil
from datetime import datetime, timedelta
from typing import Any

print("Starting generation of realistic seed data...")

# --- Configuration ---
NUM_USERS = 150
NUM_TRACKS = 500
NUM_EVENTS = 25000
GENRES = ["Pop", "Rock", "Hip-Hop", "Jazz", "Electronic", "Classical", "Country"]
ARTISTS = [f"Artist {i}" for i in range(1, 51)]

# --- 1. Generate Songs ---
songs: dict[str, Any] = []
for i in range(1, NUM_TRACKS + 1):
    songs.append({
        "trackId": 100 + i,
        "title": f"Song Title {i}",
        "artist": random.choice(ARTISTS),
        "genre": random.choice(GENRES),
        "durationMs": random.randint(120000, 300000) # 2 to 5 minutes
    })

with open("songs.json", "w") as f:
    json.dump(songs, f, indent=2)
print(f"Generated {len(songs)} songs in songs.json")

# --- 2. Generate User Personas ---
personas = []
for i in range(1, NUM_USERS + 1):
    personas.append({
        "userId": i,
        "name": f"User {i}",
        "preferredGenres": random.sample(GENRES, random.randint(1, 3))
    })

with open("personas.json", "w") as f:
    json.dump(personas, f, indent=2)
print(f"Generated {len(personas)} user personas in personas.json")

# --- 3. Generate Listening History ---
listening_history = []
for _ in range(NUM_EVENTS):
    persona = random.choice(personas)
    
    # User is more likely to listen to songs in their preferred genres
    if random.random() < 0.8: # 80% chance to pick a preferred genre
        genre = random.choice(persona["preferredGenres"])
        possible_songs = [s for s in songs if s["genre"] == genre]
    else: # 20% chance to explore
        possible_songs = songs

    song = random.choice(possible_songs)

    # Simulate different event types
    event_type_roll = random.random()
    if event_type_roll < 0.7:
        event_type = "complete_listen"
    elif event_type_roll < 0.85:
        event_type = "like"
    else:
        event_type = "skip"

    listening_history.append({
        "userId": persona["userId"],
        "trackId": song["trackId"],
        "eventType": event_type,
        "timestamp": (datetime.utcnow() - timedelta(days=random.randint(0, 365))).isoformat() + "Z"
    })

with open("listening_history.json", "w") as f:
    json.dump(listening_history, f, indent=2)
print(f"Generated {len(listening_history)} listening events in listening_history.json")

# --- 4. Move generated files to the service directory ---
script_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.join(script_dir, '..', 'MusicRecommendationService', 'Data')
os.makedirs(target_dir, exist_ok=True)

source_files = ["songs.json", "personas.json", "listening_history.json"]
for file_name in source_files:
    if os.path.exists(file_name):
        shutil.move(file_name, os.path.join(target_dir, file_name))
        print(f"Moved {file_name} to {target_dir}")

print("\nSeed data generation and placement complete.")
print("The .NET service can now load the data on startup.")