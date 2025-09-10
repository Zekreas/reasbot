import discord
from discord.ext import commands

class ReasMoney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="param", aliases=["p"])
    @commands.is_owner()
    async def kacparamvar(self, ctx):
        """Check how much money Reas has."""
        await ctx.send("Reas'ın **1,000,000,000,000,000** parası var.")
    
async def setup(bot):
    await bot.add_cog(ReasMoney(bot))