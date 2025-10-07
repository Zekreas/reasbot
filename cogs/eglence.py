import discord
from discord.ext import commands
import random

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gaytest", aliases=["gay", "gtest"])
    async def gaytesti(self, ctx, member: discord.Member = None):
        """Etiketlenen kişi için (ya da yazan kişi) gay testini yapar."""
        target = member or ctx.author
        gay_rate = random.randint(0, 100)
        await ctx.send(f"🏳️‍🌈 **{target.display_name}** gaylik oranı: **%{gay_rate}** 🌈")

def setup(bot):
    bot.add_cog(Eglence(bot))