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

def convert_tmdb_to_doc(tmdb_result):
    # Map TMDb fields to your Mongo-style doc structure
    return {
        "_id": tmdb_result["id"],
        "title": tmdb_result["title"],
        "release_year": int(tmdb_result["release_date"][:4]) if "release_date" in tmdb_result else "N/A",
        "overview": tmdb_result.get("overview", ""),
        "vote_average": tmdb_result.get("vote_average", 0.0),
        "original_language": tmdb_result.get("original_language", ""),
        "genre_ids": tmdb_result.get("genre_ids", [])
    }

def search_tmdb(query, limit=5):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": API_KEY,
        "query": query,
        "include_adult": False,
        "language": "en-US",
        "page": 1
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        time.sleep(0.2)

        results = data.get("results", [])[:limit]

        return results

    except requests.exceptions.RequestException as e:
        print(f"❌ TMDb API error: {e}")
        return []

    except Exception as e:
        print(f"❌ Unexpected TMDb error: {e}")
        return []

