import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from datetime import datetime, timedelta

class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
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
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quiz_users (
                    id TEXT PRIMARY KEY,
                    daily_correct INTEGER DEFAULT 0,
                    last_reset TEXT
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
    
    @app_commands.command(name="soru", description="Oyun hakkında soru iste")
    async def quiz(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1")
            question_data = await cursor.fetchone()
            
            if question_data is None:
                await interaction.response.send_message("Şu anda soru bulunmuyor!", ephemeral=True)
                return
            
            question_id, question, opt_a, opt_b, opt_c, opt_d, correct = question_data
            
            cursor = await db.execute(
                "SELECT daily_correct, last_reset FROM quiz_users WHERE id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            if result is None:
                await db.execute(
                    "INSERT INTO quiz_users (id, daily_correct, last_reset) VALUES (?, ?, ?)",
                    (user_id, 0, today)
                )
                await db.commit()
                daily_correct = 0
            else:
                daily_correct, last_reset = result
                if last_reset != today:
                    await db.execute(
                        "UPDATE quiz_users SET daily_correct = 0, last_reset = ? WHERE id = ?",
                        (today, user_id)
                    )
                    await db.commit()
                    daily_correct = 0
            
            remaining_coins = max(0, 3 - daily_correct)
            
            embed = discord.Embed(
                title="🎮 Oyun Sorusu",
                description=f"{question}\n\n**A**)  {opt_a}\n**B**)  {opt_b}\n**C**)  {opt_c}\n**D**)  {opt_d}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Bugün kazanabileceğin coin sayısı: {remaining_coins}")
            
            view = QuizView(user_id, correct, self.db_path, daily_correct)
            await interaction.response.send_message(embed=embed, view=view)

class QuizView(discord.ui.View):
    def __init__(self, user_id, correct_answer, db_path, daily_correct):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.correct_answer = correct_answer
        self.db_path = db_path
        self.daily_correct = daily_correct
        self.answered = False
    
    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        if self.answered:
            await interaction.response.send_message("Bu soruya zaten cevap verildi!", ephemeral=True)
            return
        
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Bu soru senin için değil!", ephemeral=True)
            return
        
        self.answered = True
        
        for item in self.children:
            item.disabled = True
        
        async with aiosqlite.connect(self.db_path) as db:
            if answer == self.correct_answer:
                if self.daily_correct < 3:
                    await db.execute(
                        "UPDATE users SET reas_coin = reas_coin + 5 WHERE id = ?",
                        (self.user_id,)
                    )
                    await db.execute(
                        "UPDATE quiz_users SET daily_correct = daily_correct + 1 WHERE id = ?",
                        (self.user_id,)
                    )
                    await db.commit()
                    await interaction.response.send_message("✅ Doğru cevap! 5 Reas Coin kazandın!", ephemeral=True)
                else:
                    await interaction.response.send_message("✅ Doğru cevap! Ancak bugünlük coin limitine ulaştın.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Yanlış cevap! Doğru cevap: {self.correct_answer}", ephemeral=True)
        
        await interaction.message.edit(view=self)
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