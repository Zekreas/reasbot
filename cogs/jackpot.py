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

    @commands.command(name="jackpot", help="Jackpot oyununa katıl! (Maks 25 coin, saatte 1 kez)")
    async def join_jackpot(self, ctx, amount: int):
        now = datetime.now()

        if now < self.jackpot_cooldown_end:
            kalan = self.jackpot_cooldown_end - now
            dakika = int(kalan.total_seconds() // 60)
            await ctx.send(f"❌ Jackpot şu anda kapalı. {dakika} dakika sonra tekrar açılacak.")
            return

        if amount < 1:
            await ctx.send("❌ Minimum 1 coin ile katılabilirsin.")
            return
        if amount > 25:
            await ctx.send("❌ Maksimum 25 coin ile katılabilirsin.")
            return

        user_id = ctx.author.id
        user_coins = await self.get_user_coins(user_id)
        if user_coins < amount:
            await ctx.send("❌ Yeterli coin'in yok.")
            return

        # Kullanıcının 1 saat cooldown kontrolü
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_join_time FROM jackpot WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            if row:
                last_time = datetime.fromisoformat(row[0])
                if last_time > now - timedelta(hours=1):
                    kalan = (last_time + timedelta(hours=1)) - now
                    dakika = int(kalan.total_seconds() // 60)
                    await ctx.send(f"⏳ Jackpot'a tekrar katılabilmek için **{dakika} dakika** beklemelisin.")
                    return

            # Katılımı kaydet
            await db.execute("""
                INSERT OR REPLACE INTO jackpot (user_id, amount, last_join_time)
                VALUES (?, ?, ?)
            """, (user_id, amount, now.isoformat()))
            await db.commit()

        # Coin düş
        await self.add_coins(user_id, -amount)
        self.jackpot_pot += amount
        await ctx.send(f"🎟️ {ctx.author.display_name} jackpot'a **{amount} coin** ile katıldı! (Toplam pot: **{self.jackpot_pot} coin**)")

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
