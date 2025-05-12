import requests, os, sys, time

from pymongo import MongoClient

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("TDMB_API_KEY")

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
collection = client["recs"]["movies"]

def enrich_movie_data(movie_id):
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"api_key": API_KEY, "language": "en-US"}

    # === 1. Get movie details ===
    details = requests.get(base_url, params=params).json()
    runtime = details.get("runtime")
    poster_path = details.get("poster_path")

    time.sleep(0.2)

    # === 2. Get credits to find director ===
    credits = requests.get(f"{base_url}/credits", params=params).json()
    director = next(
        (member["name"] for member in credits.get("crew", []) if member["job"] == "Director"),
        None
    )

    time.sleep(0.2)

    # === 3. Get watch providers (US region) ===
    providers_resp = requests.get(f"{base_url}/watch/providers", params=params).json()
    watch_providers = providers_resp.get("results", {}).get("US", {}).get("flatrate", [])
    provider_names = [p["provider_name"] for p in watch_providers]

    time.sleep(0.2)

    # === 4. Update MongoDB doc ===
    update = {
        "$set": {
            "runtime": runtime,
            "director": director,
            "watch_providers": provider_names,
            "poster_path": poster_path
        }
    }

    result = collection.update_one({"_id": movie_id}, update)
    print(f"✅ Updated movie {movie_id}: {result.modified_count} modified")
