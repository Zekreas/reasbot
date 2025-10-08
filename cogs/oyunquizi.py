import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random

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