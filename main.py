import discord, os, logging, sys

sys.path.append("..")

from discord.ext import commands

from dotenv import load_dotenv

from pymongo import MongoClient, UpdateOne
from datetime import datetime

from utils.bot_utils import *
from utils.mongo_utils import *
from utils.sheets_utils import *

load_dotenv()

token = os.getenv("DISCORD_TOKEN")

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)

tmdb_token = os.getenv("TDMB_API_KEY")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()

intents.message_content = True
intents.members = True

herbie = commands.Bot(command_prefix='!', intents=intents)

@herbie.event
async def on_ready():
    print(f'We have logged in as {herbie.user}')
    print('------')

@herbie.command()
async def ping(ctx):
    await ctx.send('Pong!')

@herbie.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author}!")

@herbie.command()
async def rec(ctx, *, query: str):
    print(f"Received query: {query}")
    await ctx.send(f"🔍 Searching for `{query}`...")

    try:
        collection = mongo_client["recs"]["movies"]

        genre_collection = mongo_client["recs"]["genres"]

        results = search_movies(query, collection, genre_collection, limit=5)
        
        if not results:
            await ctx.send("No results found.")

            return

        for idx, movie in enumerate(results, 1):
            print(f"{idx}. {movie} ({type(movie)})")

        embed = discord.Embed(
            title="🎬 Which movie did you mean?",
            description="Select one of the buttons below to record your recommendation.",
            color=discord.Color.blue()
        )

        for i, movie in enumerate(results, 1):
            title = movie.get("title", "Untitled")
            year = movie.get("release_year", "N/A")
            overview = movie.get("overview", "No overview available.")[:300]

            embed.add_field(
                name=f"{i}. {title} ({year})",
                value=f"**Overview:** {overview}...",
                inline=False
            )

        view = MovieSelectionView(results, collection, ctx.author.id, query=query)
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # ✅ This enables on_timeout to reply properly

    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("❌ Mongo search failed.")

@herbie.command()
async def top(ctx, count: int = 5):
    collection = mongo_client["recs"]["movies"]
    top_movies = list(
        collection.find({
            "tallies": {"$gt": 0},
            "watched": {"$ne": True}
        }).sort("tallies", -1).limit(count)
    )

    if not top_movies:
        await ctx.send("📭 No top movies found.")
        return

    description = "\n".join(format_movie_entry(m, i) for i, m in enumerate(top_movies))

    embed = discord.Embed(
        title="📈 Top Recommended Movies",
        description=description,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@herbie.command(name="poll")
@commands.has_any_role("Camp Counselor (Mod)", "The Eldtrich One", "Ritual Sacrifice", "Crypt Keeper", "Final Girl")
async def poll(ctx, count: int = 5):
    collection = mongo_client["recs"]["movies"]
    emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    if count > 10:
        count = 10

    top_movies = list(
        collection.find({
            "tallies": {"$gt": 0},
            "watched": {"$ne": True}
        }).sort("tallies", -1).limit(count)
    )

    if not top_movies:
        await ctx.send("📭 Not enough movies to create a poll.")
        return

    description = "\n".join(format_movie_entry(m, i, emoji_list) for i, m in enumerate(top_movies))

    poll_msg = await ctx.send(f"🗳️ **Vote for the next movie!**\n\n{description}")

    for i in range(len(top_movies)):
        await poll_msg.add_reaction(emoji_list[i])

@herbie.command(name="cross")
@commands.has_any_role("Camp Counselor (Mod)", "The Eldtrich One", "Ritual Sacrifice", "Crypt Keeper", "Final Girl")
async def cross(ctx, *, query: str):
    collection = mongo_client["recs"]["movies"]

    # Split input like: "The Witch, 2015"
    parts = query.rsplit(",", 1)

    if len(parts) != 2:
        await ctx.send("❌ Format must be: `!cross <title>, <year>` (e.g. `!cross The Witch, 2015`)")
        return

    title = parts[0].strip()
    try:
        year = int(parts[1].strip())
    except ValueError:
        await ctx.send("❌ Year must be a number. Try `!cross The Witch, 2015`.")
        return

    # Find by title and year
    movie = collection.find_one({
        "title": {"$regex": f"^{title}$", "$options": "i"},
        "release_year": year
    })

    if not movie:
        await ctx.send(f"❌ No movie found with title '{title}' and year {year}.")
        return

    # Update DB
    collection.update_one(
        {"_id": movie["_id"]},
        {
            "$set": {
                "watched": True,
                "watched_on": discord.utils.utcnow()
            }
        }
    )

    # Update sheet
    updated_movie = collection.find_one({"_id": movie["_id"]})
    try:
        append_to_google_sheet(updated_movie)
    except Exception as e:
        print(f"❌ Google Sheet update failed: {e}")
        await ctx.send(f"✅ Marked **{movie['title']}, ({year})** as watched, but failed to update the sheet.")
        return

    await ctx.send(f"✅ Marked **{movie['title']}, ({year})** as watched and updated the sheet.")

@herbie.command(name="watched")
async def watched(ctx, count: int = 5):
    collection = mongo_client["recs"]["movies"]
    movies = list(collection.find({"watched": True}).sort("watched_on", -1).limit(count))

    if not movies:
        await ctx.send("📭 No watched movies yet.")
        return

    embed = discord.Embed(
        title="✅ Recently Watched Movies",
        color=discord.Color.green()
    )

    for i, movie in enumerate(movies):
        line = format_movie_entry(movie, i)
        watched_on = movie.get("watched_on")
        date = watched_on.strftime("%Y-%m-%d %I:%M %p") if watched_on else "Unknown"
        embed.add_field(name=line, value=f"🗓️ Watched on: {date}", inline=False)

    await ctx.send(embed=embed)

@herbie.command(name="intro")
async def intro(ctx):
    with open("misc/help.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Discord allows up to 6000 characters per message, embed field is shorter (~1024 per field value)
    if len(content) > 4000:
        await ctx.send("📄 Help file is too long. Uploading as a file instead.", file=discord.File("misc/help.md"))
    else:
        embed = discord.Embed(title="📖 Herbie Help", description=content, color=discord.Color.blurple())
        await ctx.send(embed=embed)

@herbie.command(name="watchlist")
async def watchlist(ctx):
    collection = mongo_client["recs"]["movies"]
    username = str(ctx.author.name)

    # Find all movies recommended by this user that are not yet watched
    movies = collection.find({
        "recommended_by": username,
        "watched": {"$ne": True}
    }).sort("tallies", -1)

    movies = list(movies)

    if not movies:
        await ctx.send("📭 You haven't recommended any unwatched movies yet!")
        return

    # Build the watchlist message
    lines = []
    for movie in movies:
        title = movie.get("title", "Untitled")
        year = movie.get("release_year", "N/A")
        tally = movie.get("tallies", 0)
        lines.append(f"• **{title}** ({year}) — 🔁 {tally} recs")

    message = f"🎬 **Your Personal Watchlist** ({len(lines)} movies):\n\n" + "\n".join(lines)

    # Try to send it as a DM
    try:
        await ctx.author.send(message)
        await ctx.send("📩 Your watchlist has been sent via DM.")
    except discord.Forbidden:
        await ctx.send("❌ I couldn't DM you. Please enable DMs from server members.")

@herbie.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingAnyRole):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        raise error

herbie.run(token, log_handler=handler, log_level=logging.DEBUG)