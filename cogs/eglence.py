import asyncio
import discord
from discord.ext import commands
import random

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gaytesti")
    async def gaytest(self, ctx, member: discord.Member = None):
            """Etiketlenen kişi (ya da yazan kişi) için eğlencelik gay testi yapar."""
            target = member or ctx.author

            loading_emoji = "<a:yukleniyor_reasbot:1425140337503895552>"
            loading_msg = await ctx.send(f"🔍 **{target.display_name}** adlı kullanıcı analiz ediliyor... {loading_emoji}")

            # Bekleme efekti
            await asyncio.sleep(random.uniform(2.0, 3.5))

            # Mesajı sil
            await loading_msg.delete()

            # Rastgele oran
            gay_rate = random.randint(0, 100)

            # Sonucu kalın biçimde gönder
            await ctx.send(f"🏳️‍🌈 **{target.display_name} gaylik oranı: %{gay_rate}** 🌈")

async def setup(bot):
    await bot.add_cog(Eglence(bot))