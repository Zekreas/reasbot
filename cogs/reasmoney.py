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
        
        # Spam koruması için cooldown sistemi
        self.message_cooldowns = {}  # {user_id: last_reward_time}
        self.message_cooldown = 40  # 4 saniye
        
        # Ses kanalı takibi
        self.voice_users = {}  # {user_id: join_time}
        self.voice_daily = {}  # {user_id: (date, coins_today)}
        self.max_voice_daily = 60  # Günlük maksimum coin
        # Database setup
        self._setup_database()
        
        # Ses ödülü task'ını başlat
        self.voice_reward_task.start()
        
    
    def _setup_database(self):
        """Database'i kurar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                reas_coin INTEGER DEFAULT 0
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
    
    @commands.command()
    @commands.is_owner()
    async def testcoins(self, ctx):
        user_id = ctx.author.id
        coins = await self.get_user_coins(user_id)
        daily_info = self.voice_daily.get(user_id)
        
        if daily_info is None:
            daily_info_text = "Henüz günlük kayıt yok"
        else:
            daily_info_text = f"Tarih: {daily_info[0]}, Bugünkü coin: {daily_info[1]}"
        
        await ctx.send(f"Şu anki coin: {coins}\nBugünkü limit: {daily_info_text}")
    # Mesaj yazma ödülü (spam korumalı)
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Sadece belirli kanallarda puan kazanılsın
        allowed_channels = [1382742472207368192, 1407256228869967943]  # Sohbet ve Animanga sohbet
        if message.channel.id not in allowed_channels:
            return
        
        user_id = message.author.id
        now = datetime.now()
        
        # Cooldown kontrolü
        if user_id in self.message_cooldowns:
            last_reward = self.message_cooldowns[user_id]
            if (now - last_reward).total_seconds() < self.message_cooldown:
                return  # Henüz çok erken
        
        # Kullanıcıyı kaydet ve 1 coin ver
        await self.add_coins(user_id, 1)
        self.message_cooldowns[user_id] = now
    
    # Ses kanalı join/leave takibi
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        user_id = member.id
        now = datetime.now()
        today = date.today()
        
        # Günlük sıfırlama kontrolü
        if user_id in self.voice_daily:
            daily_date, coins_today = self.voice_daily[user_id]
            if daily_date != today:
                self.voice_daily[user_id] = (today, 0)
        else:
            self.voice_daily[user_id] = (today, 0)
        
        # Ses kanalına katıldı
        if before.channel is None and after.channel is not None:
            self.voice_users[user_id] = now
        
        # Ses kanalından ayrıldı
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_users:
                join_time = self.voice_users[user_id]
                duration = (now - join_time).total_seconds()
                minutes = int(duration // 60)
                
                if minutes >= 2:
                    coins = minutes // 2
                    # Günlük limiti kontrol et
                    _, coins_today = self.voice_daily[user_id]
                    coins_to_add = min(coins, self.max_voice_daily - coins_today)
                    if coins_to_add > 0:
                        await self.add_coins(user_id, coins_to_add)
                        self.voice_daily[user_id] = (today, coins_today + coins_to_add)
                
                del self.voice_users[user_id]
        
        # Kanal değiştirdi
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            if user_id in self.voice_users:
                join_time = self.voice_users[user_id]
                duration = (now - join_time).total_seconds()
                minutes = int(duration // 60)
                
                if minutes >= 2:
                    coins = minutes // 2
                    _, coins_today = self.voice_daily[user_id]
                    coins_to_add = min(coins, self.max_voice_daily - coins_today)
                    if coins_to_add > 0:
                        await self.add_coins(user_id, coins_to_add)
                        self.voice_daily[user_id] = (today, coins_today + coins_to_add)
            
            self.voice_users[user_id] = now

    # Ses ödül task
    @tasks.loop(minutes=2)
    async def voice_reward_task(self):
        if not self.voice_users:
            return
        
        now = datetime.now()
        today = date.today()
        
        for user_id, join_time in self.voice_users.items():
            # Günlük sıfırlama kontrolü
            if user_id in self.voice_daily:
                daily_date, coins_today = self.voice_daily[user_id]
                if daily_date != today:
                    self.voice_daily[user_id] = (today, 0)
            else:
                self.voice_daily[user_id] = (today, 0)
            
            # 1 dakikadan fazla seste kalanlara ödül
            if (now - join_time).total_seconds() >= 60:
                _, coins_today = self.voice_daily[user_id]
                coins_to_add = min(1, self.max_voice_daily - coins_today)
                if coins_to_add > 0:
                    await self.add_coins(user_id, coins_to_add)
                    self.voice_daily[user_id] = (today, coins_today + coins_to_add)
                
                # Bir sonraki periyot için zamanı güncelle
                self.voice_users[user_id] = now

    @voice_reward_task.before_loop
    async def before_voice_task(self):
        await self.bot.wait_until_ready()
    

    @commands.command(name="deneme", aliases=["test"])
    async def test_command(self, ctx):
        """Test komutu"""
        await ctx.send("Bot çalışıyor!")

    # Coin görüntüleme komutu
    @commands.command(name="coins", aliases=["coin", "bakiye"])
    async def show_coins(self, ctx, member: discord.Member = None):
        """Kullanıcının coin miktarını gösterir"""
        if member is None:
            member = ctx.author
        
        coins = await self.get_user_coins(member.id)
        
        embed = discord.Embed(
            title="💰 Reas Coin Bakiyesi",
            description=f"{member.display_name}: **{coins:,}** coin",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    # Leaderboard komutu
    @commands.command(name="top", aliases=["leaderboard", "sıralama"])
    async def leaderboard(self, ctx, limit: int = 10):
        """En zengin kullanıcıları gösterir"""
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
        """Cog kaldırılırken temizlik"""
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