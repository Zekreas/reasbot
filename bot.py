import json
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
import requests
import asyncio
import datetime
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True

# Komutlar için prefix (ön ek) belirliyoruz
bot = commands.Bot(command_prefix="r!", intents=intents)

@bot.command()
@commands.has_permissions(administrator=True)
async def selamla(ctx, *, yazilanyazi: str):
    await ctx.message.delete()
    await ctx.send("Maraba")
    
TARGET_HOUR = 18   # 09:00'da mesaj atacak (24 saat formatı)
TARGET_MINUTE = 31
kanalid = 1404106504138915961  # Buraya hedef kanal ID'sini girin

@bot.command()
@commands.has_permissions(administrator=True)
async def topla(ctx, sayi1: int, sayi2: int):
    toplam = sayi1 + sayi2
    await ctx.send(f"Sonuç: {toplam}")

@bot.event
async def on_ready():
    print(f"{bot.user} giriş yaptı ✅")
    rastgele_anime_gonder.start(kanalid)



"""@tasks.loop(seconds=30)
async def deneme():
    channel = bot.get_channel(kanalid)
    await channel.send("Deneme mesajı")  # Kanalda deneme mesajı gönderiyoruz
    print("Deneme mesajı gönderildi")  # Konsola mesaj yazdırıyoruz
"""
""" async def ornekembed(ctx):
    embed = discord.Embed(
        title="Başlık Buraya",
        description="📝 Bu bir örnek açıklamadır. Soluna emoji ekledik!",
        color=discord.Color.green()
    )
    
    embed.set_footer(text="Alt bilgi buraya")
    embed.set_image(url="https://i.imgur.com/xyz.png")  # İstersen sabit bir resim
    
    await ctx.send(embed=embed)
"""



def kanalbulunamadi(ctx):
    return ctx.send("Kanal bulunamadı. Lütfen geçerli bir kanal ID'si girin.")

@tasks.loop(seconds=30)
async def rastgele_anime_gonder(kanalid: int):
    channel = bot.get_channel(kanalid)
    if channel is None:
        print(f"Kanal bulunamadı: {kanalid}")
        return

    now = datetime.datetime.now()
    if now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE:
        anime = get_rastgele_anime()
        puan = anime['score'] if anime['score'] is not None else 'Veri yok'
        rank = anime['rank'] if anime['rank'] is not None else 'Veri yok'
        bolumsayisi = anime['episodes'] if anime['episodes'] is not None else 'Veri yok'

        description = f"""
        ⭐ Puan: {puan}
        🎬 Sıralama: {rank}
        📺 Bölüm Sayısı: {bolumsayisi}
        """

        embed = discord.Embed(
            title=anime['title'],
            url=anime['url'],
            description=description,
            color=discord.Color.blue()
        )
        embed.set_image(url=anime['image_url'])

        mesaj = await channel.send(embed=embed)

        await mesaj.add_reaction("<:begendim:1404143732638613594>")
        await mesaj.add_reaction("<:begenmedim:1405956641991561246>")

        thread = await channel.create_thread(
            name="Yorumlar",
            message=mesaj,
            auto_archive_duration=1440
        )
        await thread.send("Burada bu anime hakkında yorum yapabilirsiniz. <:selam:1384247246924677313>")

        # Aynı dakikada tekrar tekrar göndermemesi için bekletiyoruz
        await asyncio.sleep(60)      


@bot.command()
@commands.has_permissions(administrator=True)
async def embedyaz(ctx):
    anime = get_rastgele_anime()
    puan = anime['score'] if anime['score'] is not None else 'Not available'
    rank = anime['rank'] if anime['rank'] is not None else 'Not available'
    bolumsayisi = anime['episodes'] if anime['episodes'] is not None else 'Not available'

    description = f"""
    ⭐ Puan: {puan}
    🎬 Sıralama: {rank}
    📺 Bölüm Sayısı: {bolumsayisi}
    """

    embed = discord.Embed(
        title=anime['title'],
        url=anime['url'],
        description=description,
        color=discord.Color.blue()
    )
    embed.set_image(url=anime['image_url'])

    # Mesajı gönderiyoruz
    mesaj = await ctx.channel.send(embed=embed)

    # Tepkileri ekliyoruz
    await mesaj.add_reaction("<:begendim:1404143732638613594>")
    await mesaj.add_reaction("<:begenmedim:1405956641991561246>")

    # Thread oluşturuyoruz
    thread = await ctx.channel.create_thread(
        name="Yorumlar",
        message=mesaj,
        auto_archive_duration=1440  # 24 saat
    )
    await thread.send("Burada bu anime hakkında yorum yapabilirsiniz. <:selam:1384247246924677313>")





def get_rastgele_anime():
    url = "https://api.jikan.moe/v4/random/anime"
    
    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            anime = data['data']
            
            # Rank kontrolü - 1000'den küçük ve type TV olmalı
            if anime['rank'] is not None and anime['rank'] <= 1000 and anime['type'] == 'TV':
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
    
    print(data)  # Debugging için veriyi yazdırıyoruz
    
    try:
        with open("anime.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Dosya yazma hatası: {e}")
    
    return {
        'title': anime['title'],
        'url': anime['url'],
        'synopsis': anime['synopsis'],
        'score': anime.get('score', 'Not available'),
        'rank': anime.get('rank', 'Not available'),
        'episodes': anime.get('episodes', 'Not available'),
        'image_url': anime['images']['jpg']['image_url']
    }









print(get_rastgele_anime())


# Tokenini buraya yapıştır
bot.run("TOKEN")