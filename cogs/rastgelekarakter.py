import discord
from discord.ext import commands, tasks
import requests
import json
import asyncio
from datetime import datetime, timedelta

# Konfigürasyon
kanalid = 1408733081543643156  # Buraya kanal ID'nizi girin
TARGET_HOUR = 14  # Hedef saat
TARGET_MINUTE = 0  # Hedef dakika

class KarakterGonderici(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rastgele_karakter_gonder.start()
    
    def get_rastgele_karakter(self):
        url = "https://api.jikan.moe/v4/random/characters"
        
        while True:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                karakter = data['data']
                
                # Karakterin adı varsa ve favori sayısı yeterli ise çık
                if karakter.get('name') and karakter.get('favorites', 0) > 4200:
                    break
                    
            except requests.RequestException as e:
                print(f"API isteği başarısız: {e}")
                continue
            except KeyError as e:
                print(f"Veri yapısında eksik alan: {e}")
                continue
            except Exception as e:
                print(f"Beklenmeyen hata: {e}")
                continue
        
        # Debugging için json kaydı
        try:
            with open("karakter.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Dosya yazma hatası: {e}")
        
        return {
            'name': karakter['name'],
            'url': karakter['url'],
            'image_url': karakter['images']['jpg']['image_url'],
            'favorites': karakter.get('favorites', 0),
            'nicknames': karakter.get('nicknames', []),
            'about': karakter.get('about', 'Bilgi yok')
        }
    
    @tasks.loop(seconds=30)
    async def rastgele_karakter_gonder(self):
        channel = self.bot.get_channel(kanalid)
        if channel is None:
            print(f"Kanal bulunamadı: {kanalid}")
            return
        print("Karakter Task loop Çalıştı")
        
        now = datetime.utcnow() + timedelta(hours=3)
        print(f"Şu an saat: {now.hour}, dakika: {now.minute}")
        print(f"Hedef saat: {TARGET_HOUR}, hedef dakika: {TARGET_MINUTE}")
        
        if now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE:
            print("Karakter gönderim zamanı geldi!")
            karakter = self.get_rastgele_karakter()
            
            favorites = karakter['favorites'] if karakter['favorites'] else 'Veri yok'
            nicknames = ', '.join(karakter['nicknames'][:3]) if karakter['nicknames'] else 'Veri yok'            
            description = f"""
            ❤️ Favori Sayısı: {favorites}
            🏷️ Diğer adları: {nicknames}
            <@&1416539102563799242>
            """
            
            embed = discord.Embed(
                title=karakter['name'],
                url=karakter['url'],
                description=description,
                color=discord.Color.purple()
            )
            embed.set_image(url=karakter['image_url'])
            embed.set_footer(text="Günün Karakteri 🌟")
            
            mesaj = await channel.send(embed=embed)
            
            await mesaj.add_reaction("❤️")
            await mesaj.add_reaction("⭐")
            await mesaj.add_reaction("👎")
            
            thread = await channel.create_thread(
                name="Karakter Yorumları",
                message=mesaj,
                auto_archive_duration=1440
            )
            await thread.send("Burada bu karakter hakkında yorum yapabilirsiniz! 💬")
            
            # Aynı dakikada tekrar tekrar göndermemesi için bekletiyoruz
            await asyncio.sleep(60)
        else:
            print("Karakter için henüz zamanı değil")
    
    @rastgele_karakter_gonder.before_loop
    async def before_rastgele_karakter_gonder(self):
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        self.rastgele_karakter_gonder.cancel()
        
    @commands.command(name='karaktergonder')
    @commands.is_owner()
    async def test_karakter_gonder(self, ctx):
        """Test komutu - Sadece bot sahibi kullanabilir"""
        channel = self.bot.get_channel(kanalid)
        if channel is None:
            await ctx.send(f"Kanal bulunamadı: {kanalid}")
            return
        
        await ctx.send("Rastgele karakter gönderiliyor...")
        
        try:
            karakter = self.get_rastgele_karakter()
            
            favorites = karakter['favorites'] if karakter['favorites'] else 'Veri yok'
            nicknames = ', '.join(karakter['nicknames'][:3]) if karakter['nicknames'] else 'Veri yok'
            about = karakter['about'][:200] + '...' if len(karakter['about']) > 200 else karakter['about']
            
            description = f"""
            ❤️ Favori Sayısı: {favorites}
            🏷️ Takma Adlar: {nicknames}
            📝 Hakkında: {about}
            <@&1406948083912278088>
            """
            
            embed = discord.Embed(
                title=karakter['name'],
                url=karakter['url'],
                description=description,
                color=discord.Color.purple()
            )
            embed.set_image(url=karakter['image_url'])
            embed.set_footer(text="Test Karakteri 🧪")
            
            mesaj = await channel.send(embed=embed)
            
            await mesaj.add_reaction("❤️")
            await mesaj.add_reaction("⭐")
            await mesaj.add_reaction("👎")
            
            thread = await channel.create_thread(
                name="Test Karakter Yorumları",
                message=mesaj,
                auto_archive_duration=1440
            )
            await thread.send("Burada bu karakter hakkında yorum yapabilirsiniz! 💬 (Test)")
            
            await ctx.send("✅ Karakter başarıyla gönderildi!")
            
        except Exception as e:
            await ctx.send(f"❌ Hata oluştu: {e}")

async def setup(bot):
    await bot.add_cog(KarakterGonderici(bot))