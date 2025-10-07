import asyncio
import discord
from discord.ext import commands
import random

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gaytesti")
    async def gaytesti(self, ctx, member: discord.Member = None):
        """Etiketlenen kişi (veya yazan kişi) için eğlencelik gay testi yapar."""
        target = member or ctx.author

        loading_emoji = "<a:yukleniyor_reasbot:1425140337503895552>"
        loading_msg = await ctx.send(f"🔍 **{target.display_name}** adlı kullanıcı analiz ediliyor... {loading_emoji}")

        # Biraz bekleme efekti (2–3 saniye)
        await asyncio.sleep(random.uniform(2.0, 3.5))

        gay_rate = random.randint(0, 100)

        # Sonuç mesajı
        await loading_msg.edit(content=f"🏳️‍🌈 **{target.display_name}** gaylik oranı: **%{gay_rate}** 🌈")

async def setup(bot):
    await bot.add_cog(Eglence(bot))