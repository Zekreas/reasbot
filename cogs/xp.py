import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import datetime, timedelta

class xp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        
        # Ses kanalı takibi
        self.voice_users = {}  # {user_id: join_time}
        
        # Database setup
        self._setup_database()
        
        # Ses ödülü task'ını başlat
        self.voice_hour_task.start()
    
    def _setup_database(self):
        """Database'i kurar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voicehour INTEGER DEFAULT 0
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
                    ON CONFLICT(user_id) DO UPDATE SET voicehour = voicehour + 1
                """, (user_id,))
                await db.commit()
    
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