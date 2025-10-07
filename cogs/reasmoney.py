import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import date, datetime, timedelta
from cogs.reascoinshop import check_channel
import random
from discord import app_commands


class ReasMoney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        
        # Spam koruması için cooldown
        self.message_cooldowns = {}  # {user_id: last_reward_time}
        self.message_cooldown = 30  # saniye

        
        # Database setup
        self._setup_database()
        
    
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
    
    #random test edici
    

    # Klasik daily komutu
    @commands.command(name="daily")
    async def daily(self, ctx):
        await self._daily_reward(ctx.author.id, ctx.send)

    # Slash komutu
    @app_commands.command(name="daily", description="Günlük ödülünü al")
    async def daily_slash(self, interaction: discord.Interaction):
        await self._daily_reward(interaction.user.id, interaction.response.send_message)

    async def _daily_reward(self, user_id, send_func):
        today = date.today().isoformat()
        await self.get_or_create_user(user_id)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                last_daily = row[0] if row else None

            if last_daily == today:
                await send_func("❌ Bugün günlük ödülünü zaten aldın. Yarın tekrar dene!")
                return

            # Ödül belirleme
            if random.random() < 0.01:
                reward = 150
            else:
                reward = random.randint(25, 80)

            await self.add_coins(user_id, reward)
            await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (today, user_id))
            await db.commit()

        buyuk_ikramiye = [
            f"🎉 Vay canına! Bugün büyük ikramiyeyi kazandın! {reward} coin kazandın! 💎",
        ]
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
        if reward == 150:
            message = random.choice(buyuk_ikramiye)
        elif reward >= 65:
            message = random.choice(high_rewards)
        elif reward >= 40:
            message = random.choice(mid_rewards)
        else:
            message = random.choice(low_rewards)
        
        await send_func(message)
    
    # Mesaj ödülü
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        allowed_channels = [1382742472207368192, 1407256228869967943, 1405203383178235936, 1405902511868608542, 1408874763522277436, 1405902511868608542, 1407345046214148208, 1404373696369524838]
        if message.channel.id not in allowed_channels:
            return
        
        user_id = message.author.id
        now = datetime.now() + timedelta(hours=3)
        
        if user_id in self.message_cooldowns:
            last_reward = self.message_cooldowns[user_id]
            if (now - last_reward).total_seconds() < self.message_cooldown:
                return
        
        await self.add_coins(user_id, 1)
        self.message_cooldowns[user_id] = now
    

    
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
        pass  

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
    await bot.tree.sync()
