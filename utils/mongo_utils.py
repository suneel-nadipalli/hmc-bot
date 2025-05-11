def atlas_fuzzy_title_search(user_query, collection, limit=5):
    pipeline = [
        {
            "$search": {
                "index": "fuzzy-match",  # You created this one
                "autocomplete": {
                    "query": user_query,
                    "path": "title",
                    "fuzzy": {
                        "maxEdits": 2,         # Allow up to 2 typos
                        "prefixLength": 1      # First char must match
                    }
                }
            }
        },
        { "$limit": limit },
        {
            "$lookup": {
                "from": "genres",
                "localField": "genre_ids",
                "foreignField": "_id",
                "as": "genre_docs"
            }
        },
        {
            "$addFields": {
                "genre_names": {
                    "$map": {
                        "input": "$genre_docs",
                        "as": "g",
                        "in": "$$g.name"
                    }
                }
            }
        },
        {
            "$project": {
                "title": 1,
                "release_year": 1,
                "genre_names": 1,
                "vote_average": 1,
                "overview": 1,
                "score": { "$meta": "searchScore" }
            }
        }
    ]

    return list(collection.aggregate(pipeline))