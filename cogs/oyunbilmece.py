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
            platform TEXT NOT NULL,
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
        
        # Boşluksuz versiyonları al
        str1_no_space = str1_norm.replace(' ', '')
        str2_no_space = str2_norm.replace(' ', '')
        
        # Tam eşleşme kontrolü
        if str1_no_space == str2_no_space:
            return 100
        
        # Uzunluk farkı çok büyükse düşük skor
        len_ratio = min(len(str1_no_space), len(str2_no_space)) / max(len(str1_no_space), len(str2_no_space))
        if len_ratio < 0.6:
            return len_ratio * 50
        
        # Karakter karşılaştırması
        matches = 0
        max_len = max(len(str1_no_space), len(str2_no_space))
        
        for i in range(min(len(str1_no_space), len(str2_no_space))):
            if str1_no_space[i] == str2_no_space[i]:
                matches += 1
        
        position_score = (matches / max_len) * 100
        
        # SequenceMatcher ile genel benzerlik
        sequence_score = SequenceMatcher(None, str1_no_space, str2_no_space).ratio() * 100
        
        # İki skoru birleştir
        final_score = (position_score * 0.6) + (sequence_score * 0.4)
            
        return final_score
    
    def check_answer(self, user_answer, correct_game, alt_names):
        """Cevabın doğru olup olmadığını kontrol et"""
        # Ana isimle karşılaştır
        similarity = self.calculate_similarity(user_answer, correct_game)
        if similarity >= 80:
            return True
        
        # Alternatif isimlerle karşılaştır
        if alt_names:
            for alt_name in alt_names.split(','):
                alt_similarity = self.calculate_similarity(user_answer, alt_name.strip())
                if alt_similarity >= 80:
                    return True
        
        return False
    
    def get_hint(self, game_name, attempt):
        """Deneme sayısına göre ipucu ver"""
        if attempt == 2:
            # 2. denemede: İlk harf
            return f"🔤 İpucu: İlk harf **{game_name[0].upper()}**"
        elif attempt == 3:
            # 3. denemede: Kelime sayısı ve harf sayısı
            word_count = len(game_name.split())
            letter_count = len(game_name.replace(' ', ''))
            if word_count > 1:
                return f"🔤 İpucu: **{word_count}** kelime, toplam **{letter_count}** harf"
            else:
                return f"🔤 İpucu: **{letter_count}** harfli tek kelime"
        return None
    
    def get_random_game(self):
        """Database'den rastgele oyun çek"""
        conn = sqlite3.connect('reas.db')
        c = conn.cursor()
        c.execute('SELECT name, genre, release_year, platform, metascore, alt_names FROM games ORDER BY RANDOM() LIMIT 1')
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'genre': result[1],
                'release_year': result[2],
                'platform': result[3],
                'metascore': result[4],
                'alt_names': result[5]
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
        embed.add_field(name="🖥️ Platform", value=game['platform'], inline=True)
        embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
        embed.add_field(name="❤️ Hak", value="4/4", inline=True)
        embed.set_footer(text="Oyun ismini yazarak cevapla! (4 hakkın var)")
        
        await ctx.send(embed=embed)
        
        # Cevap bekleme fonksiyonu
        def check(m):
            return (m.author == ctx.author and 
                    m.channel == ctx.channel and 
                    not m.content.startswith('r!') and
                    ctx.author.id in self.active_games)
        
        # Oyun döngüsü
        while ctx.author.id in self.active_games and self.active_games[ctx.author.id]['attempts'] < 4:
            try:
                # Kullanıcının cevabını bekle (60 saniye timeout)
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                
                # Oyun silinmiş mi kontrol et (iptal komutu için)
                if ctx.author.id not in self.active_games:
                    break
                
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
                    embed.add_field(name="🖥️ Platform", value=game['platform'], inline=True)
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
                        embed.add_field(name="🖥️ Platform", value=game['platform'], inline=True)
                        embed.add_field(name="⭐ Metascore", value=f"{game['metascore']}/100", inline=True)
                        
                        # İpucu ekle
                        hint = self.get_hint(game['name'], attempts)
                        if hint:
                            embed.add_field(name="💡 İpucu", value=hint, inline=False)
                        
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
                        embed.add_field(name="🖥️ Platform", value=game['platform'], inline=True)
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
                if ctx.author.id in self.active_games:
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