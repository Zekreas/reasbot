import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
from difflib import SequenceMatcher

class GameGuess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # {user_id: game_data}
        self.init_db()
    
    def init_db(self):
        """Database'i başlat"""
        conn = sqlite3.connect('reas.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            genre TEXT NOT NULL,
            release_year INTEGER NOT NULL,
            metascore INTEGER NOT NULL,
            alt_names TEXT
        )''')
        conn.commit()
        conn.close()
    
    def normalize_text(self, text):
        """Metni normalize et (büyük/küçük harf, boşluk, özel karakter)"""
        text = text.lower().strip()
        # Türkçe karakterleri çevir
        replacements = {
            'ş': 's', 'ı': 'i', 'ğ': 'g', 
            'ü': 'u', 'ö': 'o', 'ç': 'c',
            'İ': 'i'
        }
        for tr_char, en_char in replacements.items():
            text = text.replace(tr_char, en_char)
        
        # Özel karakterleri kaldır, sadece harf ve rakam bırak
        text = ''.join(c for c in text if c.isalnum() or c.isspace())
        # Fazla boşlukları tek boşluğa indir
        text = ' '.join(text.split())
        return text
    
    def calculate_similarity(self, str1, str2):
        """İki string arasındaki benzerlik oranını hesapla"""
        str1_norm = self.normalize_text(str1)
        str2_norm = self.normalize_text(str2)
        
        # Tam eşleşme
        if str1_norm == str2_norm:
            return 100
        
        # Birisi diğerini içeriyor mu?
        if str1_norm in str2_norm or str2_norm in str1_norm:
            return 85
        
        # SequenceMatcher ile benzerlik
        ratio = SequenceMatcher(None, str1_norm, str2_norm).ratio()
        return ratio * 100
    
    def check_answer(self, user_answer, correct_game, alt_names):
        """Cevabın doğru olup olmadığını kontrol et"""
        # Ana isimle karşılaştır
        if self.calculate_similarity(user_answer, correct_game) >= 75:
            return True
        
        # Alternatif isimlerle karşılaştır
        if alt_names:
            for alt_name in alt_names.split(','):
                if self.calculate_similarity(user_answer, alt_name.strip()) >= 75:
                    return True
        
        return False
    
    def get_random_game(self):
        """Database'den rastgele oyun çek"""
        conn = sqlite3.connect('reas.db')
        c = conn.cursor()
        c.execute('SELECT name, genre, release_year, metascore, alt_names FROM games ORDER BY RANDOM() LIMIT 1')
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'genre': result[1],
                'release_year': result[2],
                'metascore': result[3],
                'alt_names': result[4]
            }
        return None
    
    @commands.command(name='oyuntahmin', aliases=['gameguess', 'gt'])
    async def game_guess(self, ctx):
        """Oyun tahmin oyunu başlat"""
        
        # Kullanıcının aktif oyunu var mı kontrol et
        if ctx.author.id in self.active_games:
            await ctx.send("❌ Zaten aktif bir oyunun var! Önce onu bitir.")
            return
        
        # Rastgele oyun çek
        game = self.get_random_game()
        if not game:
            await ctx.send("❌ Database'de oyun bulunamadı! Önce oyun eklemelisin.")
            return
        
        # Oyun bilgilerini sakla
        self.active_games[ctx.author.id] = {
            'game': game,
            'attempts': 0,
            'max_attempts': 4
        }
        
        # Embed oluştur
        embed = discord.Embed(
            title="🎮 Oyun Tahmin Oyunu",
            description="Aşağıdaki bilgilere göre oyunu tahmin et!",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎯 Tür", value=game['genre'], inline=True)
        embed.add_field(name="📅 Çıkış Yılı", value=game['release_year'], inline=True)
        embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
        embed.add_field(name="❤️ Hak", value="4/4", inline=False)
        embed.set_footer(text="Oyun ismini yazarak cevapla! (4 hakkın var)")
        
        await ctx.send(embed=embed)
        
        # Cevap bekleme fonksiyonu
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        # Oyun döngüsü
        while self.active_games[ctx.author.id]['attempts'] < 4:
            try:
                # Kullanıcının cevabını bekle (60 saniye timeout)
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                
                user_answer = msg.content
                attempts = self.active_games[ctx.author.id]['attempts'] + 1
                self.active_games[ctx.author.id]['attempts'] = attempts
                remaining = 4 - attempts
                
                # Cevabı kontrol et
                if self.check_answer(user_answer, game['name'], game['alt_names']):
                    # DOĞRU CEVAP
                    embed = discord.Embed(
                        title="✅ Doğru Bildin!",
                        description=f"**{game['name']}** oyununu {attempts} denemede buldun!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="🎯 Tür", value=game['genre'], inline=True)
                    embed.add_field(name="📅 Çıkış Yılı", value=game['release_year'], inline=True)
                    embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
                    embed.add_field(name="🎉 Deneme", value=f"{attempts}/4", inline=True)
                    
                    await ctx.send(embed=embed)
                    del self.active_games[ctx.author.id]
                    break
                else:
                    # YANLIŞ CEVAP
                    if remaining > 0:
                        embed = discord.Embed(
                            title="❌ Yanlış Cevap",
                            description=f"Kalan hak: **{remaining}**",
                            color=discord.Color.orange()
                        )
                        embed.add_field(name="🎯 Tür", value=game['genre'], inline=True)
                        embed.add_field(name="📅 Çıkış Yılı", value=game['release_year'], inline=True)
                        embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
                        embed.set_footer(text="Tekrar dene!")
                        await ctx.send(embed=embed)
                    else:
                        # HAKLAR BİTTİ
                        embed = discord.Embed(
                            title="💀 Kaybettin!",
                            description=f"Doğru cevap: **{game['name']}**",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="🎯 Tür", value=game['genre'], inline=True)
                        embed.add_field(name="📅 Çıkış Yılı", value=game['release_year'], inline=True)
                        embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
                        
                        await ctx.send(embed=embed)
                        del self.active_games[ctx.author.id]
                        break
                        
            except asyncio.TimeoutError:
                # ZAMAN AŞIMI
                embed = discord.Embed(
                    title="⏰ Süre Doldu!",
                    description=f"Doğru cevap: **{game['name']}**",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                del self.active_games[ctx.author.id]
                break
    
    @commands.command(name='oyuniptal', aliases=['cancelgame'])
    async def cancel_game(self, ctx):
        """Aktif oyunu iptal et"""
        if ctx.author.id in self.active_games:
            game_name = self.active_games[ctx.author.id]['game']['name']
            del self.active_games[ctx.author.id]
            await ctx.send(f"✅ Oyun iptal edildi! Doğru cevap: **{game_name}**")
        else:
            await ctx.send("❌ Aktif bir oyunun yok!")

async def setup(bot):
    await bot.add_cog(GameGuess(bot))