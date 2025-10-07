import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Select
import aiosqlite
import random
from discord import app_commands

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"

    @commands.command(name="gaytesti")
    async def gaytest(self, ctx, member: discord.Member = None):
            """Etiketlenen kişi (ya da yazan kişi) için eğlencelik gay testi yapar."""
            target = member or ctx.author

            loading_emoji = "<a:yukleniyor_reasbot:1425140337503895552>"
            loading_msg = await ctx.send(f"🔍 **{target.display_name}** adlı kullanıcı analiz ediliyor... {loading_emoji}")

            # Bekleme efekti
            await asyncio.sleep(random.uniform(2.0, 3.5))

            # Mesajı sil
            await loading_msg.delete()

            chance = random.random()  # 0.0 - 1.0 arası sayı
            if chance < 0.60:
                gay_rate = random.randint(70, 100)
            elif chance < 0.90:
                gay_rate = random.randint(0, 40)
            else:
                gay_rate = random.randint(50, 80)

            result_text = f"🏳️‍🌈 **{target.display_name} adlı kullanıcının gay oranı: %{gay_rate}** 🌈"

            await ctx.send(result_text)


    # 📘 Anime ekleme komutu
    @commands.command(name="animeekle")
    @commands.has_permissions(administrator=True)
    async def animeekle(self, ctx, *, veri: str):
        """
        Yeni anime(ler) ekler.
        Tekli ekleme: !animeekle Naruto 🍥🥷🔥🍃
        Toplu ekleme: !animeekle OnePiece 🏴‍☠️🌊🍖🧢 | DemonSlayer 🗡️👹🚂🌸 | DeathNote 📓🍎💀🕯️
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS anime_quiz (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    emojis TEXT NOT NULL
                )
            """)
            await db.commit()

            # " | " ile ayrılmışsa toplu ekleme
            entries = [x.strip() for x in veri.split("|")]
            added, skipped = [], []

            for entry in entries:
                try:
                    name, emojis = entry.rsplit(" ", 1)
                except ValueError:
                    await ctx.send(f"❌ Hatalı format: `{entry}` — boşlukla ayrılmış olmalı.")
                    continue

                # Zaten var mı kontrol et
                async with db.execute("SELECT 1 FROM anime_quiz WHERE name = ?", (name,)) as cursor:
                    exists = await cursor.fetchone()

                if exists:
                    skipped.append(name)
                else:
                    await db.execute("INSERT INTO anime_quiz (name, emojis) VALUES (?, ?)", (name, emojis))
                    added.append(name)

            await db.commit()

        msg = []
        if added:
            msg.append(f"✅ Eklendi: {', '.join(added)}")
        if skipped:
            msg.append(f"⚠️ Zaten var: {', '.join(skipped)}")

        await ctx.send("\n".join(msg) if msg else "⚠️ Hiçbir anime eklenmedi.")


    # ⚡ Anime bilmece slash komutu
    @discord.slash_command(description="Emoji ipuçlarından animeyi tahmin et!")
    async def animebilmece(self, ctx: discord.ApplicationContext, anime: Option(str, "Tahmin ettiğin anime", autocomplete=True)):
        await ctx.defer()  # cevap gecikirse yükleme göster

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name, emojis FROM anime_quiz") as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await ctx.respond("❌ Hiç anime bulunamadı!")
            return

        # Kullanıcının seçtiği animeyi bul
        selected = next((r for r in rows if r[0] == anime), None)
        if selected:
            await ctx.respond(f"🧩 **Seçtiğin anime:** {selected[0]} {selected[1]}")
        else:
            await ctx.respond("❌ Anime bulunamadı!")


    # ⚡ Autocomplete fonksiyonu
    @animebilmece.autocomplete("anime")
    async def anime_autocomplete(self, ctx: discord.AutocompleteContext):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name FROM anime_quiz") as cursor:
                all_animes = await cursor.fetchall()

        # Kullanıcı yazdığına göre filtrele
        query = ctx.value.lower() if ctx.value else ""
        choices = [a[0] for a in all_animes if query in a[0].lower()]

        # En fazla 25 seçenek dönebilir
        return choices[:25]


        await ctx.send(f"# 🧩 **Anime bilmece:** {correct[1]}", view=view)
async def setup(bot):
    await bot.add_cog(Eglence(bot))
    await bot.tree.sync()