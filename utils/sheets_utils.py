import gspread, os, sys, base64, json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from babel import Locale

sys.path.append("../..")

from dotenv import load_dotenv

from pymongo import MongoClient

key_data = base64.b64decode(os.getenv("GOOGLE_SHEETS_KEY_BASE64")).decode("utf-8")

# Parse as dictionary
key_dict = json.loads(key_data)

# Google Sheets setup (run once at startup)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
gs_client = gspread.authorize(creds)

# Sheet details
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
SHEET_TAB_NAME = "Herbie's Rec List"

sheet = gs_client.open_by_key(SHEET_ID).worksheet(SHEET_TAB_NAME)

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)

# MongoDB setup
genre_collection = mongo_client["recs"]["genres"]

def get_language_name(code):
    try:
        return Locale("en").languages.get(code, code.upper())
    except:
        return code.upper()

def format_runtime(minutes):
    if not minutes:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} hr {mins} min"

def format_datetime(dt):
    return dt.strftime("%Y-%m-%d %I:%M %p")  # e.g. 2025-05-11 02:21 AM

def get_genre_names(genre_ids):
    genre_docs = genre_collection.find({"_id": {"$in": genre_ids}})
    return [g["name"] for g in genre_docs]

def append_to_google_sheet(doc):

    print(f"Appending to Google Sheet: {doc}")

    genre_names = get_genre_names(doc.get("genre_ids", []))
    language = get_language_name(doc.get("original_language", ""))
    runtime = format_runtime(doc.get("runtime"))
    last_recommended = format_datetime(doc["last_recommended"]) if doc.get("last_recommended") else "N/A"

    vote_average = doc.get("vote_average")
    rating_display = f"{round(vote_average, 1)} / 10" if isinstance(vote_average, (int, float)) else "N/A"

    watched = "Yes" if doc.get("watched") else "No"
    watched_on = format_datetime(doc.get("watched_on")) if doc.get("watched_on") else "N/A"

    print("Gotten all data for Google Sheet.")

    row = [
        doc.get("title", "N/A"),
        language,
        doc.get("overview", "N/A"),
        ", ".join(genre_names) or "N/A",
        doc.get("director", "N/A"),
        doc.get("release_year", "N/A"),
        runtime,
        rating_display,
        ", ".join(doc.get("watch_providers", [])) or "N/A",
        doc.get("tallies", 0),
        last_recommended,
        doc.get("last_recommended_by", "N/A"),
        watched,
        watched_on 
    ]

    print("Row data prepared for Google Sheet.")

    title = doc.get("title", "N/A")
    found_cells = sheet.findall(title)  # Get all matching cells, if any

    print(found_cells)

    if found_cells:
        print(f"Found {len(found_cells)} cells with title '{title}'.")
        cell = found_cells[0]  # Use the first match
        row_num = cell.row
        print(f"📝 Found existing row for '{title}' at row {row_num}. Updating...")

        sheet.update(f"A{row_num}:N{row_num}", [row])
        print(f"✅ Updated row for '{title}'.")
    else:
        print(f"📝 No existing row found for '{title}'. Appending new row...")
        sheet.append_row(row)
        print(f"➕ Appended new row for '{title}'.")

