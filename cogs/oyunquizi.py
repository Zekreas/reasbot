import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random

from cogs.reascoinshop import check_channel

class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        self.active_users = {}  # <--- kullanıcı bazlı aktif soru takibi
        self.bot.loop.create_task(self.setup_database())

    
    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL
                )
            """)
            
            count = await db.execute("SELECT COUNT(*) FROM quiz_questions")
            result = await count.fetchone()
            
            if result[0] == 0:
                await db.execute("""
                    INSERT INTO quiz_questions (question, option_a, option_b, option_c, option_d, correct_answer)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "Hangi oyun, açık dünya, suç temalı ve multiplayer modlarıyla bilinir?",
                    "Minecraft",
                    "Grand Theft Auto V",
                    "League of Legends",
                    "Fortnite",
                    "B"
                ))
            
            await db.commit()
    @app_commands.command(name="oyunquizi", description="Oyun hakkında soru iste")
    async def quiz(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Eğer kullanıcı zaten bir soru çözüyorsa
        if user_id in self.active_users:
            await interaction.response.send_message(
                "⚠️ Önceki soruyu bitirmeden yeni soru açamazsın!", ephemeral=True
            )
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1")
            question_data = await cursor.fetchone()
            
            if question_data is None:
                await interaction.response.send_message("Şu anda soru bulunmuyor!", ephemeral=False)
                return
            
            question_id, question, opt_a, opt_b, opt_c, opt_d, correct = question_data
            
            embed = discord.Embed(
                title="🎮 Oyun Sorusu",
                description=f"{question}\n\n**A**)  {opt_a}\n**B**)  {opt_b}\n**C**)  {opt_c}\n**D**)  {opt_d}",
                color=discord.Color.blue()
            )
            
            view = QuizView(user_id, correct, self)
            self.active_users[user_id] = view  # <--- kullanıcıyı aktif sorulara ekle
            await interaction.response.send_message(embed=embed, view=view)
    

    @app_commands.command(name="oyunekle", description="Veritabanına yeni oyun ekle (Sadece Moderatörler)")
    @app_commands.describe(
        name="Oyun adı",
        genre="Oyun türü",
        metascore="Metascore puanı",
        alt_names="Alternatif isimler (opsiyonel)",
        release_year="Çıkış yılı (opsiyonel)",
        platform="Platform (opsiyonel)"
    )
    async def oyunekle(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        genre: str, 
        metascore: int,
        alt_names: str = None,
        release_year: int = None,
        platform: str = None
    ):
        # Moderatör kontrolü
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için moderatör yetkisine sahip olmalısın!", ephemeral=True)
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO games (name, genre, metascore, alt_names, release_year, platform)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, genre, metascore, alt_names, release_year, platform))
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Oyun Eklendi",
            description=f"**{name}** başarıyla veritabanına eklendi!",
            color=discord.Color.green()
        )
        embed.add_field(name="Tür", value=genre, inline=True)
        embed.add_field(name="Metascore", value=str(metascore), inline=True)
        if release_year:
            embed.add_field(name="Çıkış Yılı", value=str(release_year), inline=True)
        if platform:
            embed.add_field(name="Platform", value=platform, inline=True)
        if alt_names:
            embed.add_field(name="Alternatif İsimler", value=alt_names, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="oyunliste", description="Veritabanındaki oyunları listele (Sadece Moderatörler)")
    @app_commands.describe(sayfa="Sayfa numarası (varsayılan: 1)")
    async def oyunliste(self, interaction: discord.Interaction, sayfa: int = 1):
        # Moderatör kontrolü
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için moderatör yetkisine sahip olmalısın!", ephemeral=True)
            return
        
        if sayfa < 1:
            await interaction.response.send_message("❌ Sayfa numarası 1'den küçük olamaz!", ephemeral=True)
            return
        
        per_page = 25
        offset = (sayfa - 1) * per_page
        
        async with aiosqlite.connect(self.db_path) as db:
            # Toplam oyun sayısını al
            count_cursor = await db.execute("SELECT COUNT(*) FROM games")
            total_games = (await count_cursor.fetchone())[0]
            
            if total_games == 0:
                await interaction.response.send_message("📋 Veritabanında henüz oyun bulunmuyor!", ephemeral=True)
                return
            
            total_pages = math.ceil(total_games / per_page)
            
            if sayfa > total_pages:
                await interaction.response.send_message(f"❌ Sadece {total_pages} sayfa var!", ephemeral=True)
                return
            
            # Sayfalanmış oyunları al
            cursor = await db.execute(
                "SELECT id, name, genre, metascore FROM games LIMIT ? OFFSET ?",
                (per_page, offset)
            )
            games = await cursor.fetchall()
        
        embed = discord.Embed(
            title="🎮 Oyun Listesi",
            description=f"Sayfa {sayfa}/{total_pages} (Toplam {total_games} oyun)",
            color=discord.Color.blue()
        )
        
        for game_id, name, genre, metascore in games:
            embed.add_field(
                name=f"ID: {game_id} - {name}",
                value=f"Tür: {genre} | Metascore: {metascore}",
                inline=False
            )
        
        embed.set_footer(text=f"Sonraki sayfa için: /oyunliste sayfa:{sayfa + 1}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="oyunsil", description="ID'sine göre oyun sil (Sadece Moderatörler)")
    @app_commands.describe(game_id="Silinecek oyunun ID'si")
    async def oyunsil(self, interaction: discord.Interaction, game_id: int):
        # Moderatör kontrolü
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için moderatör yetkisine sahip olmalısın!", ephemeral=True)
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Önce oyunun var olup olmadığını kontrol et
            cursor = await db.execute("SELECT name FROM games WHERE id = ?", (game_id,))
            game = await cursor.fetchone()
            
            if game is None:
                await interaction.response.send_message(f"❌ ID {game_id} ile eşleşen oyun bulunamadı!", ephemeral=True)
                return
            
            # Oyunu sil
            await db.execute("DELETE FROM games WHERE id = ?", (game_id,))
            await db.commit()
        
        embed = discord.Embed(
            title="🗑️ Oyun Silindi",
            description=f"**{game[0]}** (ID: {game_id}) veritabanından silindi!",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)



class QuizView(discord.ui.View):
    def __init__(self, user_id, correct_answer, cog: Quiz):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.correct_answer = correct_answer
        self.answered = False
        self.cog = cog  # <--- cog referansı ile kullanıcıyı aktiflerden çıkaracağız

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        if self.answered:
            await interaction.response.send_message("Bu soruya zaten cevap verildi!", ephemeral=True)
            return
        
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Bu soru senin için değil!", ephemeral=True)
            return
        
        self.answered = True
        
        if answer == self.correct_answer:
            await interaction.response.send_message(f"✅ Doğru cevap, {interaction.user.mention}!", ephemeral=False)
        else:
            await interaction.response.send_message(f"❌ Yanlış cevap! Doğru cevap: {self.correct_answer}, {interaction.user.mention}", ephemeral=False)
        
        # Tüm butonları pasif yap
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Kullanıcıyı aktif sorulardan çıkar
        if self.user_id in self.cog.active_users:
            del self.cog.active_users[self.user_id]
        
        self.stop()

    
    @discord.ui.button(label="A", style=discord.ButtonStyle.primary, row=0)
    async def button_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "A")
    
    @discord.ui.button(label="B", style=discord.ButtonStyle.primary, row=0)
    async def button_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "B")
    
    @discord.ui.button(label="C", style=discord.ButtonStyle.primary, row=0)
    async def button_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "C")
    
    @discord.ui.button(label="D", style=discord.ButtonStyle.primary, row=0)
    async def button_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "D")

async def setup(bot):
    await bot.add_cog(Quiz(bot))