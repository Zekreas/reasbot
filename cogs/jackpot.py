import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
import random
from datetime import datetime, timedelta

class Jackpot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        self.jackpot_pot = 0
        self.jackpot_open = False
        self.jackpot_end_time = None
        self.jackpot_cooldown_end = datetime.min  # 2 saat cooldown
        self.jackpot_task_running = False

    # Jackpot tablosunu kur
    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jackpot (
                    user_id INTEGER,
                    amount INTEGER,
                    last_join_time TEXT
                )
            """)
            await db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.setup_database()
        print("[JACKPOT] Jackpot sistemi başlatıldı!")

    async def add_coins(self, user_id, amount):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, reas_coin) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET reas_coin = reas_coin + ?
            """, (user_id, amount, amount))
            await db.commit()

    async def get_user_coins(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT reas_coin FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def finish_jackpot(self):
        """Jackpot bitir ve kazananı seç"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, amount FROM jackpot") as cursor:
                entries = await cursor.fetchall()
            await db.execute("DELETE FROM jackpot")
            await db.commit()

        if not entries:
            self.jackpot_pot = 0
            self.jackpot_open = False
            self.jackpot_cooldown_end = datetime.now() + timedelta(hours=2)
            return

        total_pot = sum(a for _, a in entries)
        winner_id, _ = random.choice(entries)
        await self.add_coins(winner_id, total_pot)

        winner = self.bot.get_user(winner_id)
        jackpot_channel_id = 1427792479427498088  # jackpot duyuru kanalı ID
        channel = self.bot.get_channel(jackpot_channel_id)
        if channel and winner:
            await channel.send(
                f"🎰 **Jackpot Sonuçları!** 🎰\n"
                f"🏆 Kazanan: **{winner.mention}**\n"
                f"💰 Ödül: **{total_pot} coin!**"
            )

        self.jackpot_pot = 0
        self.jackpot_open = False
        self.jackpot_cooldown_end = datetime.now() + timedelta(hours=2)
        self.jackpot_task_running = False

    async def start_jackpot_timer(self):
        """30 dakikalık süreyi başlat"""
        self.jackpot_end_time = datetime.now() + timedelta(minutes=30)
        self.jackpot_open = True
        self.jackpot_task_running = True
        await asyncio.sleep(30 * 60)  # 30 dakika bekle
        await self.finish_jackpot()

    @commands.command(name="jackpot", help="Jackpot oyununa katıl! (Toplam 25 coin sınırı)")
    async def join_jackpot(self, ctx, amount: int):
        now = datetime.now()

        if now < self.jackpot_cooldown_end:
            kalan = self.jackpot_cooldown_end - now
            dakika = int(kalan.total_seconds() // 60)
            await ctx.send(f"❌ Jackpot şu anda kapalı. {dakika} dakika sonra tekrar açılacak.")
            return

        if amount <= 0:
            await ctx.send("❌ En az 1 coin yatırabilirsin.")
            return

        if amount > 25:
            await ctx.send("❌ Tek seferde en fazla 25 coin yatırabilirsin.")
            return

        user_id = ctx.author.id
        user_coins = await self.get_user_coins(user_id)
        if user_coins < amount:
            await ctx.send("❌ Yeterli coin'in yok.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Kullanıcının toplam yatırdığı miktarı al
            async with db.execute("SELECT amount FROM jackpot WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                mevcut_miktar = row[0] if row else 0

            yeni_toplam = mevcut_miktar + amount
            if yeni_toplam > 25:
                kalan = 25 - mevcut_miktar
                await ctx.send(f"❌ Toplamda en fazla 25 coin yatırabilirsin. Şu anda {mevcut_miktar} yatırmışsın, en fazla **{kalan}** coin daha ekleyebilirsin.")
                return

            # Katılımı kaydet veya güncelle
            await db.execute("""
                INSERT INTO jackpot (user_id, amount, last_join_time)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET amount = amount + ?
            """, (user_id, amount, now.isoformat(), amount))
            await db.commit()

        # Coin düş
        await self.add_coins(user_id, -amount)
        self.jackpot_pot += amount
        await ctx.send(f"🎟️ {ctx.author.display_name} jackpot'a {amount} coin ekledi! (Toplam yatırımı: {yeni_toplam}/25 | Pot: {self.jackpot_pot} coin)")

        # Jackpot başlat
        if not self.jackpot_task_running:
            await self.start_jackpot_timer()

    @commands.command(name="jackpotdurum", aliases=["jackpotstatus"])
    async def jackpot_status(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT SUM(amount) FROM jackpot") as cursor:
                row = await cursor.fetchone()
                total_pot = row[0] if row and row[0] else 0
            async with db.execute("SELECT COUNT(user_id) FROM jackpot") as cursor:
                count = (await cursor.fetchone())[0]

        if self.jackpot_open:
            kalan = self.jackpot_end_time - datetime.now()
            dakika = int(kalan.total_seconds() // 60)
        else:
            dakika = 0

        embed = discord.Embed(
            title="🎰 Jackpot Durumu",
            description=(
                f"👥 Katılımcı sayısı: **{count}**\n"
                f"💰 Toplam pot: **{total_pot} coin**\n"
                f"🕐 Süre kalan: **{dakika} dakika**" if dakika > 0 else "Jackpot şu anda kapalı."
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Jackpot(bot))
