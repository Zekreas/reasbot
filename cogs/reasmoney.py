import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, List
import requests

class WordleGame:
    def __init__(self, word: str, player_id: int):
        self.word = word.upper()
        self.player_id = player_id
        self.attempts = []
        self.max_attempts = 6
        self.game_over = False
        self.won = False
    
    def make_guess(self, guess: str) -> Optional[List[tuple]]:
        """Tahmin yap ve sonucu döndür. Her harf için (harf, durum) tuple'ı döner."""
        guess = guess.upper()
        
        if len(guess) != len(self.word):
            return None
        
        if guess in [g[0] for g in self.attempts]:
            return None
        
        result = []
        word_letters = list(self.word)
        guess_letters = list(guess)
        
        # İlk olarak doğru pozisyondaki harfleri işaretle (yeşil)
        for i in range(len(guess)):
            if guess_letters[i] == word_letters[i]:
                result.append((guess_letters[i], '🟩'))
                word_letters[i] = None
                guess_letters[i] = None
        
        # Sonra yanlış pozisyondaki harfleri işaretle (sarı)
        for i in range(len(guess)):
            if guess_letters[i] is not None:
                if guess_letters[i] in word_letters:
                    result.insert(i, (guess_letters[i], '🟨'))
                    word_letters[word_letters.index(guess_letters[i])] = None
                else:
                    result.insert(i, (guess_letters[i], '⬜'))
        
        self.attempts.append((guess, result))
        
        if guess == self.word:
            self.game_over = True
            self.won = True
        elif len(self.attempts) >= self.max_attempts:
            self.game_over = True
        
        return result

    def get_board(self) -> str:
        """Oyun tahtasını string olarak döndür."""
        board = "**WORDLE OYUNU**\n\n"
        
        for guess, result in self.attempts:
            board += ''.join([f"{emoji}" for letter, emoji in result])
            board += f" `{guess}`\n"
        
        # Kalan tahmin haklarını göster
        remaining = self.max_attempts - len(self.attempts)
        for _ in range(remaining):
            board += '⬛' * len(self.word) + "\n"
        
        board += f"\n**Tahmin:** {len(self.attempts)}/{self.max_attempts}"
        
        if self.game_over:
            if self.won:
                board += f"\n\n🎉 **Tebrikler! Kelimeyi buldunuz!**"
            else:
                board += f"\n\n❌ **Oyun bitti! Kelime:** `{self.word}`"
        
        return board


class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, WordleGame] = {}
        
        # Türkçe 5 harfli kelimeler
        self.words = [
            # Eşyalar
            "ÇANTA", "TAHTA", "ÇEKİÇ", "RADYO", "KAĞIT",
            "SEHPA", "DOLAP", "KALEM", "KAŞIK", "BIÇAK",
            "TABAK", "TABLO", "LAMBA", "TEPSİ", "KİLİT",
            "RENDE", "AYRAÇ", "MAKAS",
            # Giysiler
            "KAZAK", "HIRKA", "CEKET", "KEMER", "FULAR",
            "KABAN", "PALTO",
            # Hayvanlar
            "YILAN", "KÖPEK", "DOMUZ", "KUMRU", "AKREP",
            "SERÇE", "TAVUK", "HOROZ", "HİNDİ", "ŞAHİN",
            "KOYUN", "KATIR", "MANDA", "TİLKİ", "GEYİK",
            "KİRPİ",
            # Sıfatlar
            "SADIK", "ZAYIF", "SAKİN", "YALIN", "ALÇAK",
            "REZİL", "EBEDİ", "EZELİ", "VAZIH", "FAKİR",
            "ASABİ", "FERAH", "GÜZEL", "NADİR", "NAZİK",
            "KİBAR", "SABİT", "YAKIN", "DERİN", "TEMİZ",
            "GİZLİ", "KUTLU", "KOLAY", "BASİT", "BEŞİR",
            "GAMLI", "LATİF", "İÇSEL", "ZEBUN", "CİMRİ",
            # Yiyecekler
            "SALÇA", "CEVİZ", "BADEM", "KEKİK", "ARMUT",
            "MARUL", "SOĞAN", "KİRAZ", "ÇİLEK", "VİŞNE",
            "KAVUN", "BAMYA", "SUSAM", "TAHİN", "REÇEL",
            "AYRAN"
        ]
    
    async def check_turkish_word(self, word: str) -> bool:
        """TDK API ile kelimenin Türkçe olup olmadığını kontrol et."""
        try:
            url = f"https://sozluk.gov.tr/gts?ara={word.lower()}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return isinstance(data, list) and len(data) > 0
            return False
        except:
            # API hata verirse, oyun durmasın diye True döndür
            return True
    
    @app_commands.command(name="wordle", description="Wordle oyununu başlat")
    async def wordle_start(self, interaction: discord.Interaction):
        """Yeni bir Wordle oyunu başlat."""
        if interaction.user.id in self.active_games:
            await interaction.response.send_message(
                "Zaten aktif bir oyununuz var! `/wordletahmin` ile devam edin veya `/wordlebitir` ile bitirin.",
                ephemeral=True
            )
            return
        
        word = random.choice(self.words)
        game = WordleGame(word, interaction.user.id)
        self.active_games[interaction.user.id] = game
        
        embed = discord.Embed(
            title="🎮 Wordle Oyunu Başladı!",
            description=f"{game.get_board()}\n\n💡 `/wordletahmin` komutu ile {len(word)} harfli kelime tahmin edin!",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="wordletahmin", description="Wordle oyununda tahmin yap")
    @app_commands.describe(kelime="Tahmin ettiğiniz kelime")
    async def wordle_guess(self, interaction: discord.Interaction, kelime: str):
        """Wordle oyununda tahmin yap."""
        if interaction.user.id not in self.active_games:
            await interaction.response.send_message(
                "Aktif bir oyununuz yok! `/wordle` ile yeni oyun başlatın.",
                ephemeral=True
            )
            return
        
        game = self.active_games[interaction.user.id]
        
        if game.game_over:
            await interaction.response.send_message(
                "Oyun bitti! `/wordle` ile yeni oyun başlatın.",
                ephemeral=True
            )
            return
        
        # Kelime uzunluğu kontrolü
        if len(kelime) != len(game.word):
            await interaction.response.send_message(
                f"❌ {len(game.word)} harfli bir kelime girmelisiniz!",
                ephemeral=True
            )
            return
        
        # Defer the response since API call might take time
        await interaction.response.defer()
        
        # TDK API ile kelime kontrolü
        is_valid = await self.check_turkish_word(kelime)
        if not is_valid:
            await interaction.followup.send(
                "❌ Bu geçerli bir Türkçe kelime değil! TDK sözlüğünde bulunamadı.",
                ephemeral=True
            )
            return
        
        result = game.make_guess(kelime)
        
        if result is None:
            await interaction.followup.send(
                f"❌ Bu kelimeyi daha önce tahmin ettiniz!",
                ephemeral=True
            )
            return
        
        color = discord.Color.green() if game.won else discord.Color.red() if game.game_over else discord.Color.blue()
        
        embed = discord.Embed(
            title="🎮 Wordle Oyunu",
            description=game.get_board(),
            color=color
        )
        
        await interaction.followup.send(embed=embed)
        
        if game.game_over:
            del self.active_games[interaction.user.id]
    
    @app_commands.command(name="wordlebitir", description="Aktif Wordle oyununu bitir")
    async def wordle_end(self, interaction: discord.Interaction):
        """Aktif Wordle oyununu bitir."""
        if interaction.user.id not in self.active_games:
            await interaction.response.send_message(
                "Aktif bir oyununuz yok!",
                ephemeral=True
            )
            return
        
        game = self.active_games[interaction.user.id]
        del self.active_games[interaction.user.id]
        
        await interaction.response.send_message(
            f"Oyun sonlandırıldı! Kelime: `{game.word}` idi.",
            ephemeral=True
        )
    
    @app_commands.command(name="wordlekurallar", description="Wordle oyun kurallarını göster")
    async def wordle_rules(self, interaction: discord.Interaction):
        """Wordle oyun kurallarını göster."""
        embed = discord.Embed(
            title="📖 Wordle Kuralları",
            description=(
                "Wordle, kelime tahmin oyunudur!\n\n"
                "**Nasıl Oynanır:**\n"
                "• `/wordle` komutu ile oyunu başlatın\n"
                "• `/wordletahmin` ile kelime tahmin edin\n"
                "• 6 tahmin hakkınız var\n\n"
                "**Renk Kodları:**\n"
                "🟩 Doğru harf, doğru pozisyon\n"
                "🟨 Doğru harf, yanlış pozisyon\n"
                "⬜ Yanlış harf\n\n"
                "**İpucu:** Sesli harflerle başlayın!"
            ),
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Wordle(bot))