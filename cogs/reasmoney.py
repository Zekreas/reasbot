import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import date, datetime, timedelta

class ReasMoney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        
        # Spam koruması için cooldown
        self.message_cooldowns = {}  # {user_id: last_reward_time}
        self.message_cooldown = 30  # saniye
        
        # Ses takibi (DB’ye taşındı, burada sadece aktif oturumlar tutuluyor)
        self.voice_users = {}  # {user_id: join_time}
        self.max_voice_daily = 160  # günlük maksimum ses coin
        
        # Database setup
        self._setup_database()
        
        # Ses ödülü task'ı
        self.voice_reward_task.start()
    
    def _setup_database(self):
        """Database tablolarını kurar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                reas_coin INTEGER DEFAULT 0,
                last_daily TEXT,
                voice_daily_date TEXT,
                voice_daily_coins INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    async def add_coins(self, user_id, amount):
        """Kullanıcıya coin ekler"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, reas_coin) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET reas_coin = reas_coin + ?
            """, (user_id, amount, amount))
            await db.commit()
    
    async def get_user_coins(self, user_id):
        """Kullanıcının coin miktarını getirir"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT reas_coin FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def get_or_create_user(self, user_id):
        """Kullanıcı kaydını getirir, yoksa oluşturur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id) VALUES (?)
            """, (user_id,))
            await db.commit()
    
    # Günlük ödül komutu
    @commands.command(name="daily")
    async def daily(self, ctx):
        user_id = ctx.author.id
        today = date.today().isoformat()
        
        await self.get_or_create_user(user_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                last_daily = row[0] if row else None
            
            if last_daily == today:
                await ctx.send("❌ Bugün günlük ödülünü zaten aldın. Yarın tekrar dene!")
                return
            
            reward = 50  # günlük ödül miktarı (istersen değiştir)
            await self.add_coins(user_id, reward)
            await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (today, user_id))
            await db.commit()
        
        await ctx.send(f"✅ Günlük ödülünü aldın! {reward} coin eklendi 💰")
    
    @commands.command( name="coinhaklarim" )
    @commands.is_owner()
    async def testcoins(self, ctx):
        user_id = ctx.author.id
        coins = await self.get_user_coins(user_id)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT voice_daily_date, voice_daily_coins FROM users WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                daily_date, coins_today = row if row else (None, 0)

        today = date.today().isoformat()
        if daily_date != today:
            coins_today = 0

        remaining_voice_coins = max(self.max_voice_daily - coins_today, 0)

        await ctx.send(
            f"Şu anki coin: {coins}\n"
            f"Bugünkü ses limiti: {remaining_voice_coins}/{self.max_voice_daily}"
        )
    # Mesaj ödülü
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        allowed_channels = [1382742472207368192, 1407256228869967943]
        if message.channel.id not in allowed_channels:
            return
        
        user_id = message.author.id
        now = datetime.now()
        
        if user_id in self.message_cooldowns:
            last_reward = self.message_cooldowns[user_id]
            if (now - last_reward).total_seconds() < self.message_cooldown:
                return
        
        await self.add_coins(user_id, 1)
        self.message_cooldowns[user_id] = now
    
    # Ses kanalına giriş/çıkış
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        user_id = member.id
        now = datetime.now()
        today = date.today().isoformat()
        
        await self.get_or_create_user(user_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT voice_daily_date, voice_daily_coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                daily_date, coins_today = row if row else (None, 0)
            
            if daily_date != today:
                coins_today = 0
                await db.execute("UPDATE users SET voice_daily_date = ?, voice_daily_coins = 0 WHERE user_id = ?", (today, user_id))
                await db.commit()
        
        if before.channel is None and after.channel is not None:
            self.voice_users[user_id] = now
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_users:
                join_time = self.voice_users[user_id]
                duration = (now - join_time).total_seconds()
                minutes = int(duration // 60)
                
                if minutes >= 2:
                    coins = minutes // 2
                    async with aiosqlite.connect(self.db_path) as db:
                        async with db.execute("SELECT voice_daily_coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
                            row = await cursor.fetchone()
                            coins_today = row[0] if row else 0
                        coins_to_add = min(coins, self.max_voice_daily - coins_today)
                        print(f"[VOICE DEBUG] user_id={user_id} coins={coins} coins_today={coins_today} coins_to_add={coins_to_add}")
                        if coins_to_add > 0:
                            await self.add_coins(user_id, coins_to_add)
                            await db.execute("UPDATE users SET voice_daily_coins = voice_daily_coins + ? WHERE user_id = ?", (coins_to_add, user_id))
                            await db.commit()
                del self.voice_users[user_id]
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            if user_id in self.voice_users:
                join_time = self.voice_users[user_id]
                duration = (now - join_time).total_seconds()
                minutes = int(duration // 60)
                
                if minutes >= 2:
                    coins = minutes // 2
                    async with aiosqlite.connect(self.db_path) as db:
                        async with db.execute("SELECT voice_daily_coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
                            row = await cursor.fetchone()
                            coins_today = row[0] if row else 0
                        coins_to_add = min(coins, self.max_voice_daily - coins_today)
                        print(f"[VOICE DEBUG] user_id={user_id} coins={coins} coins_today={coins_today} coins_to_add={coins_to_add}")
                        if coins_to_add > 0:
                            await self.add_coins(user_id, coins_to_add)
                            await db.execute("UPDATE users SET voice_daily_coins = voice_daily_coins + ? WHERE user_id = ?", (coins_to_add, user_id))
                            await db.commit()
            self.voice_users[user_id] = now
    
    @tasks.loop(minutes=2)
    async def voice_reward_task(self):
        if not self.voice_users:
            return
        
        now = datetime.now()
        today = date.today().isoformat()
        
        for user_id, join_time in list(self.voice_users.items()):
            if (now - join_time).total_seconds() >= 60:
                await self.get_or_create_user(user_id)
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT voice_daily_date, voice_daily_coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        row = await cursor.fetchone()
                        daily_date, coins_today = row if row else (None, 0)
                    
                    if daily_date != today:
                        coins_today = 0
                        await db.execute("UPDATE users SET voice_daily_date = ?, voice_daily_coins = 0 WHERE user_id = ?", (today, user_id))
                        await db.commit()
                    
                    coins_to_add = min(1, self.max_voice_daily - coins_today)
                    if coins_to_add > 0:
                        await self.add_coins(user_id, coins_to_add)
                        await db.execute("UPDATE users SET voice_daily_coins = voice_daily_coins + ? WHERE user_id = ?", (coins_to_add, user_id))
                        await db.commit()
                self.voice_users[user_id] = now
    
    @voice_reward_task.before_loop
    async def before_voice_task(self):
        await self.bot.wait_until_ready()
    
    
    # Leaderboard
    @commands.command(name="top", aliases=["leaderboard", "sıralama"])
    async def leaderboard(self, ctx, limit: int = 10):
        if limit > 20:
            limit = 20
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, reas_coin FROM users 
                ORDER BY reas_coin DESC LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await ctx.send("Henüz hiç coin kazanan yok!")
            return
        embed = discord.Embed(
            title="🏆 Reas Coin Sıralaması",
            color=discord.Color.gold()
        )
        description = ""
        for i, (user_id, coins) in enumerate(rows, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Kullanıcı {user_id}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} {name}: **{coins:,}** coin\n"
        embed.description = description
        await ctx.send(embed=embed)
    
    def cog_unload(self):
        self.voice_reward_task.cancel()

async def setup(bot):
    await bot.add_cog(ReasMoney(bot))
