import discord, os, logging, sys, base64

sys.path.append("..")

from discord.ext import commands

from dotenv import load_dotenv

from pymongo import MongoClient, UpdateOne
from datetime import datetime

from utils.bot_utils import *
from utils.mongo_utils import *

load_dotenv()

# Decode and write the service account key file
key_data = base64.b64decode(os.environ["GOOGLE_SHEETS_KEY_BASE64"])

with open("service_account.json", "wb") as f:
    f.write(key_data)

token = os.getenv("DISCORD_TOKEN")

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)

tmdb_token = os.getenv("TDMB_API_KEY")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()

intents.message_content = True
intents.members = True

herbie = commands.Bot(command_prefix='/', intents=intents)

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

        results = atlas_fuzzy_title_search(query, collection, limit=5)
        
        if not results:
            await ctx.send("No results found.")

            return

        view = MovieSelectionView(results, collection, ctx.author.id)
        await ctx.send("🎬 Which movie did you mean?", view=view)

    except Exception as e:
        print(f"🔥 Atlas Search error: {e}")
        await ctx.send("❌ Mongo search failed.")

@herbie.command()
async def top(ctx, count: int = 5):
    collection = mongo_client["recs"]["movies"]
    top_movies = collection.find(
        {"tallies": {"$gt": 0}}
    ).sort("tallies", -1).limit(count)

    if not top_movies:
        await ctx.send("No recommended movies yet.")
        return

    response = "**🎬 Top Recommended Movies:**\n"
    for i, movie in enumerate(top_movies, start=1):
        response += f"{i}. **{movie['title']}** — {movie['tallies']} tally{'ies' if movie['tallies'] != 1 else ''}\n"

    await ctx.send(response)

@herbie.command()
async def poll(ctx, count: int = 5):
    collection = mongo_client["recs"]["movies"]
    top_movies = list(collection.find(
        {"tallies": {"$gt": 0}}
    ).sort("tallies", -1).limit(count))

    if not top_movies:
        await ctx.send("Not enough data to create a poll.")
        return

    if len(top_movies) > 10:
        await ctx.send("⚠️ Maximum of 10 options for polling.")
        top_movies = top_movies[:10]

    emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    description = ""

    for i, movie in enumerate(top_movies):
        description += f"{emoji_list[i]} **{movie['title']}**\n"

    poll_msg = await ctx.send(f"🗳️ **Vote for your favorite movie:**\n\n{description}")

    # Add reactions to the poll
    for i in range(len(top_movies)):
        await poll_msg.add_reaction(emoji_list[i])


herbie.run(token, log_handler=handler, log_level=logging.DEBUG)