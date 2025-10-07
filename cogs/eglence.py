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

            chance = random.random()  # 0.0 - 1.0 arası sayı
            if chance < 0.65:
                gay_rate = random.randint(70, 100)
            elif chance < 0.90:
                gay_rate = random.randint(0, 40)
            else:
                gay_rate = random.randint(50, 80)

            result_text = f"🏳️‍🌈 **{target.display_name} adlı kullanıcının gay oranı: %{gay_rate}** 🌈"

            await ctx.send(result_text)

async def setup(bot):
    await bot.add_cog(Eglence(bot))