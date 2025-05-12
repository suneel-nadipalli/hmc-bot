from rapidfuzz import fuzz
import re

def smart_score(query, title):
    q, t = query.lower(), title.lower()
    w = {
        "exact": 40,
        "fuzzy": 30,
        "prefix": 15,
        "substring": 10,
        "token": 5
    }

    score = 0

    # Exact match
    if q == t:
        score += w["exact"]
    
    # Fuzzy similarity
    fuzzy = fuzz.token_set_ratio(q, t) / 100
    score += fuzzy * w["fuzzy"]

    # Prefix match
    if t.startswith(q):
        score += w["prefix"]

    # Substring bonus (penalize distant matches)
    if q in t:
        idx = t.find(q)
        distance_penalty = max(1, idx)
        score += w["substring"] * (1 / distance_penalty)

    # Token overlap
    q_tokens = set(re.findall(r"\w+", q))
    t_tokens = set(re.findall(r"\w+", t))
    overlap = len(q_tokens & t_tokens)
    score += w["token"] * (overlap / max(1, len(q_tokens)))

    return round(score, 2)

import re
from rapidfuzz import fuzz, distance

def smart_score_v2(query, title):
    q, t = query.lower(), title.lower()
    w = {
        "exact": 40,
        "fuzzy": 30,
        "prefix": 15,
        "substring": 10,
        "token": 5,
        "edit": 5  # improvement 1
    }

    score = 0

    # Exact match
    if q == t:
        score += w["exact"]

    # Fuzzy similarity
    fuzzy = fuzz.token_set_ratio(q, t) / 100
    score += fuzzy * w["fuzzy"]

    # Prefix match
    if t.startswith(q):
        score += w["prefix"]

    # Substring bonus (with position-based penalty)
    if q in t:
        idx = t.find(q)
        score += w["substring"] * (1 / max(1, idx))

    # Token overlap
    q_tokens = set(re.findall(r"\w+", q))
    t_tokens = set(re.findall(r"\w+", t))
    overlap = len(q_tokens & t_tokens)
    score += w["token"] * (overlap / max(1, len(q_tokens)))

    # Edit distance bonus for short queries
    if len(q) <= 5:
        edit_dist = distance.Levenshtein.distance(q, t)
        if edit_dist <= 1:
            score += w["edit"]

    # Length penalty (improvement 4)
    length_penalty = min(1.0, len(t) / 30)
    score *= 0.9 + 0.1 * (1 / length_penalty)

    return round(min(score, 100) / 100, 3)

def search_movies(query, collection, genre_collection, limit=5):
    # Step 1: Pull candidate documents from MongoDB
    raw_docs = list(collection.find({}, {
        "_id": 1,
        "title": 1,
        "release_year": 1,
        "overview": 1,
        "vote_average": 1,
        "genre_ids": 1
    }))

    # Step 2: Score all documents using smart_score_v2
    scored = []
    for doc in raw_docs:
        if "title" in doc:
            score = smart_score_v2(query, doc["title"])
            if score > 0:
                doc["score"] = score
                scored.append(doc)

    # Step 3: Sort by score
    top_docs = sorted(scored, key=lambda x: -x["score"])[:limit]

    # Step 4: Populate genre names from genre_ids
    genre_map = {g["_id"]: g["name"] for g in genre_collection.find()}
    for doc in top_docs:
        doc["genre_names"] = [
            genre_map.get(gid) for gid in doc.get("genre_ids", []) if genre_map.get(gid)
        ]

    # Step 5: Keep only desired fields
    return [
        {
            "_id": doc["_id"],
            "title": doc.get("title"),
            "release_year": doc.get("release_year"),
            "overview": doc.get("overview"),
            "vote_average": doc.get("vote_average"),
            "genre_names": doc.get("genre_names", []),
            "score": doc["score"]
        }
        for doc in top_docs
    ]
