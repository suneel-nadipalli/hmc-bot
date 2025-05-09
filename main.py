import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")

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
    await ctx.send('Pong 2!')

@herbie.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author}!")

herbie.run(token, log_handler=handler, log_level=logging.DEBUG)