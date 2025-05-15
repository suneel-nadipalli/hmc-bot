import discord, os, sys

sys.path.append("../..")

from utils.tmdb_utils import *

from utils.sheets_utils import *

def format_movie_entry(movie, index=None, emoji_list=None):
    title = movie.get("title", "Untitled")
    year = movie.get("release_year", "N/A")
    tally = movie.get("tallies", 0)
    rating = movie.get("vote_average", 0.0)
    emoji = emoji_list[index] if emoji_list and index is not None else f"{index + 1}." if index is not None else "•"

    return f"{emoji} **{title}** ({year}) — ⭐ {round(rating, 1)} | 🔁 {tally} recs"


class NoneOfTheseButton(discord.ui.Button):
    def __init__(self, query, movies_collection, user_id):
        super().__init__(label="None of These", style=discord.ButtonStyle.secondary)
        self.query = query
        self.movies_collection = movies_collection
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):

        self.view.interaction_completed = True

        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You're not allowed to respond to this.", ephemeral=True)
            return

        if self.view.is_finished():
            await interaction.response.send_message("⏱️ This interaction has expired. Please try again.", ephemeral=True)
            return

        await interaction.response.defer()

        # 🔄 Fallback to TMDb search API
        tmdb_results = search_tmdb(query=self.query)

        if not tmdb_results:
            await interaction.followup.send("❌ Couldn't find any matches on TMDb either.")
            return

        # 🧠 Enrich TMDb results into your Mongo-style dicts
        fallback_docs = []

        for m in tmdb_results:
            doc = convert_tmdb_to_doc(m)

            # Check if the movie already exists by TMDb ID
            existing = self.movies_collection.find_one({"_id": doc["_id"]})

            if not existing:
                inserted = self.movies_collection.insert_one(doc)
                doc["_id"] = inserted.inserted_id  # Mongo might overwrite _id if it was a collision
            else:
                doc["_id"] = existing["_id"]  # Reuse the one already in the DB

            fallback_docs.append(doc)


        # 🎬 Send new view + embed
        embed = discord.Embed(
            title="🎬 TMDb Search Results",
            description="Select a movie below if it's the one you meant.",
            color=discord.Color.purple()
        )

        for i, movie in enumerate(fallback_docs, 1):
            title = movie.get("title", "Untitled")
            year = movie.get("release_year", "N/A")
            overview = str(movie.get("overview", "No overview available."))[:300]
            embed.add_field(
                name=f"{i}. {title} ({year})",
                value=f"**Overview:** {overview}...",
                inline=False
            )

        await interaction.followup.send(
            embed=embed,
            view=MovieSelectionView(fallback_docs, self.movies_collection, self.user_id)
        )


class MovieSelectionView(discord.ui.View):
    def __init__(self, results, movies_collection, user_id, query=None):
        super().__init__(timeout=10)
        self.user_id = user_id
        self.results = results
        self.message = None  # will be set later
        self.interaction_completed = False  # ✅ Add this flag

        print(f"MovieSelectionView initialized with {len(results)} results.")

        for movie in results:
            label = f"{movie['title']} ({movie.get('release_year', 'N/A')})"
            self.add_item(MovieSelectButton(label, movie, movies_collection, user_id))
        
        self.add_item(NoneOfTheseButton(query=query, movies_collection=movies_collection, user_id=user_id))

    async def on_timeout(self):
        print("⚠️ View timed out.")

        if self.interaction_completed:
            return  # ✅ Skip timeout message if a user completed it

        # Disable buttons visually (optional)
        for item in self.children:
            item.disabled = True

        # Safely send a message
        if self.message:
            try:
                await self.message.channel.send(
                    content=f"⏱️ This interaction expired. Please use `!rec` again.",
                    reference=self.message,  # optional: threads it under original
                    mention_author=False
                )
            except Exception as e:
                print(f"❌ Failed to send timeout message: {e}")


class MovieSelectButton(discord.ui.Button):
    def __init__(self, label, movie, movies_collection, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.movie = movie
        self.movies_collection = movies_collection  # ✅ fixed
        self.user_id = user_id

        print(f"MovieSelectButton initialized with label: {label}")

    async def callback(self, interaction: discord.Interaction):
        self.view.interaction_completed = True

        print(f"[INTERACTION] user: {interaction.user.id}, allowed: {self.user_id}, expired: {self.view.is_finished()}")

        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You're not allowed to respond to this.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.handle_selection(interaction)

    async def handle_selection(self, interaction):
        try:
            movie_id = self.movie["_id"]
            username = str(interaction.user.name)

            print(f"User {username} selected movie ID: {movie_id}")

            doc = self.movies_collection.find_one({"_id": movie_id})
            print(f"Document found: {doc}")

            if not doc:
                await interaction.followup.send("❌ Couldn’t find that movie in the database.")
                return

            # 🛑 Check if they've already recommended this
            if username in doc.get("recommended_by", []):
                await interaction.followup.send(
                    f"⚠️ You've already recommended **{doc.get('title', 'Untitled')}**."
                )
                return

            if not all([doc.get("runtime"), doc.get("director")]):
                enrich_movie_data(movie_id)

            # Update in DB
            self.movies_collection.update_one(
                {"_id": movie_id},
                {
                    "$inc": {"tallies": 1},
                    "$set": {
                        "last_recommended": discord.utils.utcnow(),
                        "last_recommended_by": username
                    },
                    "$addToSet": {"recommended_by": username}
                }
            )

            # Fetch the updated doc for accurate tally + watched flags
            updated_doc = self.movies_collection.find_one({"_id": movie_id})
            tally = updated_doc.get("tallies", 1)
            title = updated_doc.get("title", "Untitled")

            # Update Google Sheet
            append_to_google_sheet(updated_doc)

            await interaction.followup.send(
                f"✅ Recommendation recorded for **{title}**.\nTotal tallies: {tally}"
            )

        except Exception as e:
            print(f"🔥 Selection error: {e}")
            await interaction.followup.send("❌ Something went wrong while processing your recommendation.")
