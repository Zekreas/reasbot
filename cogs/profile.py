import discord
from discord.ext import commands
import aiosqlite

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"  # Veritabanı yolu

    @commands.command(name="profil", aliases=["profile"])
    async def profile(self, ctx, member: discord.Member = None):
        """Kullanıcının profilini gösterir."""
        member = member or ctx.author  # Eğer bir kullanıcı belirtilmezse komutu kullanan kişi

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT reas_coin, voicehour, messagecount FROM users WHERE user_id = ?",
                (member.id,)
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            await ctx.send("Kullanıcı bulunamadı veya verisi yok.")
            return

        reas_coin, voicehour, messagecount = row

        # Embed hazırlıyoruz
        embed = discord.Embed(
            title=f"{member.display_name} Profili",
            color=discord.Color.blue()
        )
        embed.description = (
            f"**Reas Coin:** {reas_coin}\n"
            f"**Toplam Ses Süresi:** {voicehour} saat\n"
            f"**Toplam Mesaj:** {messagecount}"
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)

        await ctx.send(embed=embed)

def setup(bot):
    await bot.add_cog(ProfileCog(bot))