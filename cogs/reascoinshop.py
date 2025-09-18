import discord
from discord.ext import commands
import aiosqlite

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def market(self, ctx):
        async with aiosqlite.connect("coins.db") as db:
            cursor = await db.execute("SELECT id, name, price, description FROM shop_items")
            items = await cursor.fetchall()

        embed = discord.Embed(title="🛒 Market", color=discord.Color.green())
        for item in items:
            embed.add_field(
                name=f"{item[0]}. {item[1]} - {item[2]}💰",
                value=item[3],
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def buy(self, ctx, item_id: int):
        user_id = ctx.author.id
        async with aiosqlite.connect("coins.db") as db:
            # Kullanıcının coinini çek
            cursor = await db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                return await ctx.send("Henüz hiç coin kazanmadın!")
            user_coins = row[0]

            # Ürün bilgisi
            cursor = await db.execute("SELECT name, price FROM shop_items WHERE id = ?", (item_id,))
            item = await cursor.fetchone()
            if not item:
                return await ctx.send("❌ Böyle bir ürün yok.")
            
            name, price = item

            # Coin yetiyor mu?
            if user_coins < price:
                return await ctx.send("💸 Yeterli coin yok.")
            
            # Coin düş
            await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, user_id))
            await db.commit()

        await ctx.send(f"✅ {ctx.author.mention}, **{name}** ürününü başarıyla satın aldın!")

async def setup(bot):
    await bot.add_cog(Shop(bot))
