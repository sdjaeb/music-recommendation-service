# generate_weekly_trends.py
import random
import os
import shutil
import csv
import json
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from tqdm import tqdm
except ImportError:
    print("Info: 'tqdm' is not installed. Progress bar will not be shown.")
    print("You can install it using: pip install tqdm (or uv pip install tqdm)")
    sys.exit(1)

# --- Configuration ---
STATE_FILE = "data_generation_state.json"
OUTPUT_DIR = "generated_data/weekly_trends"
HISTORICAL_DATA_DIR = "generated_data"

def truncate_generated_data():
    """
    Removes the state file and the weekly trends directory to reset
    the incremental generation process.
    """
    print("Truncating weekly data and resetting state...")
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print(f"Removed state file: {STATE_FILE}")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"Removed weekly trends directory: {OUTPUT_DIR}")
    print("Reset complete.")

# --- State Management ---
def load_state() -> datetime:
    """Loads the last generated date from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return datetime.strptime(state['last_generated_date'], '%Y-%m-%d')
    else:
        # If no state file, the historical data ended on 2024-12-31.
        # This is the starting point for the first weekly batch.
        return datetime(2024, 12, 31)

def save_state(new_date: datetime):
    """Saves the new last generated date to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_generated_date': new_date.strftime('%Y-%m-%d')}, f)

# --- Data Loading ---
def load_dimension_data(file_path: str) -> List[Dict[str, Any]]:
    """Loads a dimension CSV into a list of dictionaries."""
    if not os.path.exists(file_path):
        print(f"Error: Historical data file not found at {file_path}", file=sys.stderr)
        print("Please run `generate_seed_data.py` first.", file=sys.stderr)
        sys.exit(1)
    
    with open(file_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        data = []
        for row in reader:
            for key, value in row.items():
                if value: # Only process non-empty strings
                    try:
                        if key.endswith('_id') or key.endswith('_ms'):
                            row[key] = int(value)
                        elif key.endswith('_popularity'):
                            row[key] = float(value)
                    except (ValueError, TypeError):
                        pass # Keep original string value if conversion fails
            data.append(row)
        return data

# --- Main Generation Logic ---
def generate_weekly_data(start_date: datetime, end_date: datetime):
    """Generates one week of listening event data."""
    print(f"Generating weekly trend data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

    songs = load_dimension_data(os.path.join(HISTORICAL_DATA_DIR, "dim_songs.csv"))
    users = load_dimension_data(os.path.join(HISTORICAL_DATA_DIR, "dim_users.csv"))

    total_days = (end_date - start_date).days
    events_per_day_avg = 20000
    event_id_counter = int(start_date.timestamp())

    output_filename = f"trends_{end_date.strftime('%Y-%m-%d')}.csv"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename)

    with open(output_filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "user_id", "track_id", "event_type", "timestamp"])

        for day_index in tqdm(range(total_days + 1), desc="Generating daily events"):
            current_date = start_date + timedelta(days=day_index)
            
            song_weights = [s['base_popularity'] for s in songs]

            events_today = int(events_per_day_avg * (1 + random.uniform(-0.2, 0.2)))
            for _ in range(events_today):
                user = random.choice(users)
                chosen_song = random.choices(songs, weights=song_weights, k=1)[0]

                event_type_roll = random.random()
                event_type = "skip"
                if event_type_roll < 0.75: event_type = "complete_listen"
                elif event_type_roll < 0.9: event_type = "like"

                event_timestamp = current_date + timedelta(seconds=random.randint(0, 86399))
                
                writer.writerow([
                    f"evt_{event_id_counter}",
                    user['user_id'],
                    chosen_song['track_id'],
                    event_type,
                    event_timestamp.isoformat() + "Z"
                ])
                event_id_counter += 1
    
    print(f"Generated {event_id_counter - int(start_date.timestamp())} events in '{output_filepath}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate weekly incremental trend data for the music service."
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Reset the state by deleting the state file and all generated weekly data.",
    )
    args = parser.parse_args()

    if args.truncate:
        truncate_generated_data()
    else:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        last_date = load_state()
        start_date = last_date + timedelta(days=1)
        end_date = start_date + timedelta(days=6)
        
        generate_weekly_data(start_date, end_date)
        save_state(end_date)
        print("\nWeekly data generation complete.")