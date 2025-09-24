import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import date, datetime, timedelta
from cogs.reascoinshop import check_channel
import random

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
    @check_channel()
    async def daily(self, ctx):
        user_id = ctx.author.id
        logkanali = 1384165277419180133
        today = date.today().isoformat()
        
        await self.get_or_create_user(user_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                last_daily = row[0] if row else None
            
            if last_daily == today:
                await ctx.send("❌ Bugün günlük ödülünü zaten aldın. Yarın tekrar dene!")
                return
            
            
            if random.random() < 0.05:  # %5 şans
                reward = 100
                # random değerini yazacak.
                logkanali.send(f"{ctx.author} {random} büyük ikramiyeyi kazandı! 100 coin!")
            else:
                reward = random.randint(15, 60)
            await self.add_coins(user_id, reward)
            await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (today, user_id))
            await db.commit()
        
        high_rewards = [
            f"✅ Günlük ödülünü aldın! 🎉 Bugün şanslı günün! {reward} coin kazandın! 💎",
            f"✅ Günlük ödülünü aldın! 🔥 Muhteşem! Bugün {reward} coin kazandın!",
        ]
        mid_rewards = [
            f"✅ Günlük ödülünü aldın! ✨ Güzel! {reward} coin kazandın. 💰",
            f"✅ Günlük ödülünü aldın! Bugün {reward} coin topladın!",
        ]
        low_rewards = [
            f"✅ Günlük ödülünü aldın! Bugünlük {reward} coin... Yarın daha iyi olabilir!",
        ]
        
        if reward == 100:
            await ctx.send("✅ Günlük ödülünü aldın! 🎉 Büyük ikramiyeyi tutturdun ve 100 coin kazandın!💎")
        elif reward >= 50:
            await ctx.send(random.choice(high_rewards))
        elif reward >= 25:
            await ctx.send(random.choice(mid_rewards))
        else:
            await ctx.send(random.choice(low_rewards))
        
    
    @commands.command(name="coinhaklarim" )
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
        
        allowed_channels = [1382742472207368192, 1407256228869967943, 1405203383178235936, 1405902511868608542, 1408874763522277436, 1405902511868608542, 1407345046214148208, 1404373696369524838]
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

    @commands.command(name="coinduzenle", aliases=["setcoins"])
    @commands.is_owner()
    async def set_coins(self, ctx, member: discord.Member, amount: int):
        if amount == 0:
            await ctx.send("Coin miktarı 0 olamaz.")
            return
        await self.add_coins(member.id, amount)
        if amount > 0:
            await ctx.send(f"✅ {member.display_name} kullanıcısına **{amount}** coin eklendi.")
        else:
            await ctx.send(f"✅ {member.display_name} kullanıcısının coininden **{-amount}** coin çıkarıldı.")

    @commands.command(name="resetcoins", aliases=["coinsıfırla"])
    @commands.is_owner()
    async def reset_coins(self, ctx, member: discord.Member):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET reas_coin = 0 WHERE user_id = ?", (member.id,))
            await db.commit()
        await ctx.send(f"✅ {member.display_name} kullanıcısının coin miktarı sıfırlandı.")


    @commands.command(name="modcoinkomutları", aliases=["modcoin"])
    @commands.is_owner()  # Sadece bot sahibi kullanabilir
    async def mod_coin_commands(self, ctx):
        """Mod coin komutlarını gösterir"""
        embed = discord.Embed(
            title="🔧 Mod Coin Komutları",
            color=discord.Color.blue()
        )
        embed.add_field(name="r!setcoins @kullanıcı miktar", value="Belirtilen kullanıcıya miktar kadar coin ekler veya çıkarır. (miktar negatif ise çıkarır)", inline=False)
        embed.add_field(name="r!resetcoins @kullanıcı", value="Belirtilen kullanıcının coin miktarını sıfırlar.", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ReasMoney(bot))
