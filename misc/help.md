# 🎬 Herbie's Horror Haven

Hey, I'm Herbie!

So you wanna throw another never-to-be-watched movie onto the never-ending list, huh?

Hey, I get it — life is hectic. I’m here to bring some order to the chaos and help you track what you and your fellow victims... I mean friends... want to watch.

---

## 🔍 !rec [movie name]

Start tracking a movie recommendation!

- You’ll be shown the closest matches from our spooky little archive.
- Pick the right one — or select **"None of These"** to search TMDb directly.
- Once chosen, I’ll log your rec, update the tally, enrich the movie data, and slap it into the spreadsheet.

---

## 📈 !top [count]

Shows the top `[count]` most-recommended but **unwatched** movies (default: 5).

- Sorted by tally count, descending.
- Watched films are respectfully excluded.

---

## 🗳️ !poll [count]

!!MODS ONLY!!

Creates a Discord poll of the top `[count]` **unwatched** movies.

- Max: 10 options (Discord's emoji limit).
- Everyone votes, winner gets 👑.
- Follow up with `!cross` to mark the winner!

---

## ✅ !cross [title], [year]

!!MODS ONLY!!

Marks a movie as **watched**.

- You must specify the exact title and year (e.g. `!cross REC, 2007`).
- This will:
  - Set the movie as watched
  - Timestamp when it was marked
  - Exclude it from polls and top recs
  - Update the Google Sheet with its final form

---

## 🎥 !watched

See the most recently watched movies.

- Returns 5 by default
- Includes watch date, rating, and rec tally

---

## 🧾 !watchlist

Sends you a **DM** of all the movies you’ve recommended that haven’t been watched yet.

- Clean, private shame.
- Updated automatically as you use `!rec` and `!cross`.

---

## 📘 !intro

Displays this very help guide.  

---

## 🧠 Final Notes

- Movie titles are matched fuzzily — close is usually good enough.
- Data is pulled and enriched from TMDb on demand.
- Everything is logged in a shared [Google Sheet](https://docs.google.com/spreadsheets/d/1Oy4f-omlnMN1dBzmdUlSkHYacWqK_2EfL6RAImfxYck/edit?usp=sharing):
  - Titles
  - Genres
  - Ratings
  - Tally counts
  - Watch status
- Only Mods can use the poll and cross commands

---

Thanks for talking to me!
Remember...call upon me responsibly. 🩸
