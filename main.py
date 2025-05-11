import discord, os, logging, sys

sys.path.append("..")

from discord.ext import commands

from dotenv import load_dotenv

from pymongo import MongoClient, UpdateOne
from datetime import datetime

from utils.bot_utils import *
from utils.mongo_utils import *

load_dotenv()

token = os.getenv("DISCORD_TOKEN")

mongo_uri = os.getenv("MONGO_URI")
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

@bot.command(name="recommend")
async def recommend(ctx, *, query: str):
    await ctx.send(f"🔍 Searching for `{query}`...")

    results = atlas_fuzzy_title_search(query, limit=5)

    if not results:
        await ctx.send("❌ No matches found. Try spelling it more accurately or using more of the title.")
        return

    # Create selection options for user
    view = MovieSelectionView(results, ctx.author.id)
    await ctx.send("🎬 Which movie did you mean?", view=view)


herbie.run(token, log_handler=handler, log_level=logging.DEBUG)