class MovieSelectionView(discord.ui.View):
    def __init__(self, results, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.results = results

        for i, movie in enumerate(results):
            label = f"{movie['title']} ({movie.get('release_year', 'N/A')})"
            self.add_item(MovieSelectButton(label=label, movie=movie, user_id=user_id))

class MovieSelectButton(discord.ui.Button):
    def __init__(self, label, movie, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.movie = movie
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You're not allowed to respond to this.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.handle_selection(interaction)

    async def handle_selection(self, interaction):
        movie_id = self.movie["_id"]
        user_id = str(interaction.user.id)

        # Check if metadata needs to be enriched (e.g. no director yet)
        doc = movies_collection.find_one({"_id": movie_id})

        update_fields = {
            "$inc": {"tallies": 1},
            "$set": {"last_recommended": discord.utils.utcnow()},
            "$addToSet": {"recommended_by": user_id}
        }

        # Optional: lazy enrichment (not shown here for brevity)

        movies_collection.update_one({"_id": movie_id}, update_fields)

        await interaction.followup.send(
            f"✅ Recommendation recorded for **{doc['title']}**. Total tallies: {doc.get('tallies', 0) + 1}"
        )
