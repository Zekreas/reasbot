import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from cogs.reascoinshop import check_channel

class xp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        
        # Ses kanalı takibi
        self.voice_users = {}  # {user_id: join_time}
        #her gün bu kanala aylık sıralama gönderilecek.
        self.ayliksiralama = 1418538714937954434 #kanal idsi
        # Database setup
        self._setup_database()
        
        # Ses ödülü task'ını başlat
        self.voice_hour_task.start()
        self.send_monthly_leaderboard.start()
    def _setup_database(self):
        """Database'i kurar"""
        conn = sqlite3.connect(self.db_path)


        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voicehour INTEGER DEFAULT 0,
                voicehourmonth INTEGER DEFAULT 0,
                messagecount INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()
    
    # Ses kanalı join/leave takibi
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        user_id = member.id
        now = datetime.now()
        
        # Ses kanalına katıldı
        if before.channel is None and after.channel is not None:
            self.voice_users[user_id] = now
        
        # Ses kanalından ayrıldı
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_users:
                del self.voice_users[user_id]
        
        # Kanal değiştirdi (aynı anda hem join hem leave)
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            # Yeni kanala katılma (zaman sıfırlamaya gerek yok, devam ediyor)
            pass

    @tasks.loop(minutes=1)
    async def voice_hour_task(self):
        """Her dakika kontrol eder, 1 saat tamamlayanları ödüllendirir"""
        if not self.voice_users:
            return
        
        now = datetime.now()
        users_to_reward = []
        
        for user_id, join_time in self.voice_users.items():
            # Tam 1 saat (3600 saniye) geçmişse
            duration = (now - join_time).total_seconds()
            if duration >= 3600:  # 1 saat = 3600 saniye
                users_to_reward.append(user_id)
                # Zamanlayıcıyı 1 saat ileriye al (bir sonraki saat için)
                self.voice_users[user_id] = now
        
        # Ödülleri dağıt
        for user_id in users_to_reward:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO users (user_id, voicehour) VALUES (?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET voicehour = voicehour + 1, voicehourmonth = voicehourmonth + 1
                """, (user_id,))
                await db.commit()
    
    @tasks.loop(hours=1)
    async def reset_monthly_task(self):
        now = datetime.now() + timedelta(hours=3)  # 3 saat ileri al
        if now.day == 1 and now.hour == 1:  # Ayın ilk günü
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET voicehourmonth = 0")
                await db.commit()
    @reset_monthly_task.before_loop
    async def before_reset_monthly_task(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def send_monthly_leaderboard(self):
        now = datetime.now() + timedelta(hours=3)  # 3 saat ileri al
        if now.hour == 23:  # Ayın ilk günü saat 00:00'da
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_id, voicehourmonth FROM users 
                    WHERE voicehourmonth > 0
                    ORDER BY voicehourmonth DESC
                    LIMIT 10
                """) as cursor:
                    top_rows = await cursor.fetchall()
            
            if not top_rows:
                return
            
            embed = discord.Embed(
                title="🎤 Aylık Ses Kanalı Sıralaması",
                color=discord.Color.gold(),
                description="İşte bu ayın en çok ses kanalında kalan kullanıcıları!"
            )
            
            description = ""
            for i, (user_id, voicehourmonth) in enumerate(top_rows, 1):
                user = self.bot.get_user(user_id)
                name = user.display_name if user else f"Kullanıcı {user_id}"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                description += f"{medal} {name}: **{voicehourmonth}** saat\n"
            
            embed.description = description
            
            channel = self.bot.get_channel(self.ayliksiralama)
            if channel:
                # Önce botun eski mesajlarını sil
                async for message in channel.history(limit=50):  # son 50 mesaja bak
                    if message.author == self.bot.user:
                        await message.delete()

                # Yeni mesajı gönder
                await channel.send(embed=embed)
        else:
            print("Aylık sıralama gönderme zamanı değil.")
    @send_monthly_leaderboard.before_loop
    async def before_send_monthly_leaderboard(self):
        await self.bot.wait_until_ready()
    
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        allowed_channels = [1382742472207368192, 1407256228869967943, 1405203383178235936, 1405902511868608542, 1408874763522277436, 1405902511868608542, 1407345046214148208, 1404373696369524838]
        if message.channel.id not in allowed_channels:
            return
        
        user_id = message.author.id
        
        # Kullanıcı her mesaj gönderdiğinde reas.db'deki messagecount değerini 1 artır. Başka bir şey yapma. cooldown olmayacak. zaten veritabanı bağlantısı yapıldı.
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, messagecount) VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET messagecount = messagecount + 1
            """, (user_id,))
            await db.commit()

    
    @commands.command(name="profil", aliases=["profile"])
    @check_channel()
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

    @commands.command(name="ayliksiralamamesaj", aliases=["mesaj", "mesajtop"])
    @check_channel()
    async def ayliksiralamamesaj(self, ctx):
        """Aylık mesaj sıralamasını gösterir"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, messagecount FROM users 
                WHERE messagecount > 0
                ORDER BY messagecount DESC
                LIMIT 10
            """) as cursor:
                top_rows = await cursor.fetchall()
        
        if not top_rows:
            await ctx.send("Henüz aylık mesaj kazanan yok!")
            return
        
        embed = discord.Embed(
            title="✉️ Aylık Mesaj Sıralaması",
            color=discord.Color.blue(),
            description="İşte bu ayın en çok mesaj atan kullanıcıları!"
        )
        
        description = ""
        for i, (user_id, messagecount) in enumerate(top_rows, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Kullanıcı {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} {name}: **{messagecount}** mesaj\n"
        
        embed.description = description
        
        await ctx.send(embed=embed)

        

    @commands.command(name="aylikgondermanuel")
    async def aylikgondermanuel(self, ctx):
        """Aylık sıralamayı manuel olarak gönderir (sadece yetkililer)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Bu komutu kullanmak için yönetici olmalısın.")
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, voicehourmonth FROM users 
                WHERE voicehourmonth > 0
                ORDER BY voicehourmonth DESC
                LIMIT 10
            """) as cursor:
                top_rows = await cursor.fetchall()
        
        if not top_rows:
            await ctx.send("Henüz aylık ses saati kazanan yok!")
            return
        
        embed = discord.Embed(
            title="🎤 Aylık Ses Kanalı Sıralaması",
            color=discord.Color.gold(),
            description="İşte bu ayın en çok ses kanalında kalan kullanıcıları!"
        )
        
        description = ""
        for i, (user_id, voicehourmonth) in enumerate(top_rows, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Kullanıcı {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} {name}: **{voicehourmonth}** saat\n"
        
        embed.description = description
        
        await ctx.send(embed=embed)

    # Ses sıralaması komutu
    @commands.command(name="voicetop", aliases=["sestop", "sesistatistikleri", "ses"])
    async def voice_leaderboard(self, ctx, limit: int = 10):
        """En çok ses kanalında duran kullanıcıları gösterir"""
        if limit > 20:
            limit = 20
        
        # Tüm kullanıcıları sıralı olarak al
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, voicehour FROM users 
                WHERE voicehour > 0
                ORDER BY voicehour DESC
            """) as cursor:
                all_rows = await cursor.fetchall()
        
        if not all_rows:
            await ctx.send("Henüz hiç ses saati kazanan yok!")
            return
        
        # İlk 10'u al
        top_rows = all_rows[:limit]
        
        embed = discord.Embed(
            title="🎤 Ses Kanalı Sıralaması",
            color=discord.Color.purple()
        )
        
        description = ""
        for i, (user_id, voicehour) in enumerate(top_rows, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Kullanıcı {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} {name}: **{voicehour}** saat\n"
        
        embed.description = description
        
        # Komutu kullanan kişinin sırasını bul
        user_rank = None
        user_hours = None
        for i, (user_id, voicehour) in enumerate(all_rows, 1):
            if user_id == ctx.author.id:
                user_rank = i
                user_hours = voicehour
                break
        
        if user_rank:
            embed.add_field(
                name="📍 Senin Sıran",
                value=f"**{user_rank}.** sıradasın - **{user_hours}** saat",
                inline=False
            )
        else:
            embed.add_field(
                name="📍 Senin Sıran",
                value="Henüz ses saatin yok!",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    def cog_unload(self):
        """Cog kaldırılırken temizlik"""
        pass

async def setup(bot):
    await bot.add_cog(xp(bot))