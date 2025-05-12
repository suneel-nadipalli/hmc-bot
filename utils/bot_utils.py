import discord, os, sys

sys.path.append("../..")

from utils.tmdb_utils import *

from utils.sheets_utils import *

class MovieSelectionView(discord.ui.View):
    def __init__(self, results, movies_collection, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.results = results

        print(f"MovieSelectionView initialized with {len(results)} results.")

        for movie in results:
            label = f"{movie['title']} ({movie.get('release_year', 'N/A')})"
            self.add_item(MovieSelectButton(label, movie, movies_collection, user_id))


class MovieSelectButton(discord.ui.Button):
    def __init__(self, label, movie, movies_collection, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.movie = movie
        self.movies_collection = movies_collection  # ✅ fixed
        self.user_id = user_id

        print(f"MovieSelectButton initialized with label: {label}")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You're not allowed to respond to this.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.handle_selection(interaction)

    async def handle_selection(self, interaction):
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
                f"⚠️ You've already recommended **{doc['title']}**."
            )
            return

        if not all([
            doc.get("runtime"),
            doc.get("director"),
            doc.get("watch_providers")
        ]):
            enrich_movie_data(movie_id)

        update_fields = {
            "$inc": {"tallies": 1},
            "$set": {
                "last_recommended": discord.utils.utcnow(),
                "last_recommended_by": username
            },
            "$addToSet": {"recommended_by": username}
        }
        
        self.movies_collection.update_one({"_id": movie_id}, update_fields)

        updated_doc = self.movies_collection.find_one({"_id": movie_id})
        tally = updated_doc.get("tallies", 1)

        print(f"Updated document: {updated_doc}")

        append_to_google_sheet(updated_doc)

        await interaction.followup.send(
            f"✅ Recommendation recorded for **{doc['title']}**.\nTotal tallies: {tally}"
        )
