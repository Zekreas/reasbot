import os
import json
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta, date
import requests
import asyncio
from dotenv import load_dotenv
from io import BytesIO
import aiohttp
import random


load_dotenv()  # .env dosyasını yükler
TOKEN = os.getenv("DISCORD_TOKEN")  # .env içindeki tokeni alır

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Üyeleri izlemek için gerekli izin
intents.guilds = True  # Sunucuları izlemek için gerekli izin
# Komutlar için prefix (ön ek) belirliyoruz
bot = commands.Bot(command_prefix="r!", intents=intents, help_command=None)

initial_extensions = []

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        initial_extensions.append(f"cogs.{filename[:-3]}")

async def load_extensions():
    for ext in initial_extensions:
        await bot.load_extension(ext)
    
TARGET_HOUR = 12   # 09:00'da mesaj atacak (24 saat formatı)
TARGET_MINUTE = 0
kanalid = 1406708938375954673  # Buraya hedef kanal ID'sini girin
SHIP_TARGET_HOUR = 17   # 09:00'da mesaj atacak (24 saat formatı)
SHIP_TARGET_MINUTE = 0
SHIP_kanalid = 1408715714503774228  # Buraya hedef kanal ID'sini girin
Gununhanti_TARGET_HOUR = 23   # 09:00'da mesaj atacak (24 saat formatı)
Gununhanti_TARGET_MINUTE = 0
gununhanti_kanalid = 1405472367068708935
girenkisisayisi = 0
cikankisisayisi = 0

# !reload komutu (sadece bot sahibi çalıştırabilir)
@bot.command()
@commands.is_owner()
async def reload(ctx, cog: str):
    """Belirtilen cog'u yeniden yükler"""
    try:
        try:
            await bot.unload_extension(f"cogs.{cog}")
        except commands.ExtensionNotLoaded:
            pass  # Yüklü değilse sorun yok
        await bot.load_extension(f"cogs.{cog}")
        await ctx.send(f"✅ `{cog}` cog başarıyla yeniden yüklendi!")
    except Exception as e:
        await ctx.send(f"❌ `{cog}` cog yüklenirken hata oluştu:\n`{e}`")



@bot.command()
@commands.has_permissions(administrator=True)
async def zaman(ctx, saat: int, dakika: int):
    """Yalnızca yöneticiler mesaj atılacak zamanı değiştirebilir"""
    global TARGET_HOUR, TARGET_MINUTE
    if 0 <= saat <= 23 and 0 <= dakika <= 59:
        TARGET_HOUR = saat
        TARGET_MINUTE = dakika
        await ctx.send(f"Mesaj gönderme zamanı ayarlandı: {TARGET_HOUR:02}:{TARGET_MINUTE:02}")
    else:
        await ctx.send("Geçersiz saat veya dakika! 0-23 saat, 0-59 dakika olmalı.")

# Yönetici olmayan kullanıcılar için özel hata mesajı
@zaman.error
async def zaman_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için yönetici yetkisine sahip olmalısın!")

@bot.command()
@commands.has_permissions(administrator=True)
async def shipzaman(ctx, saat: int, dakika: int):
    """Yalnızca yöneticiler mesaj atılacak zamanı değiştirebilir"""
    global SHIP_TARGET_HOUR, SHIP_TARGET_MINUTE
    if 0 <= saat <= 23 and 0 <= dakika <= 59:
        SHIP_TARGET_HOUR = saat
        SHIP_TARGET_MINUTE = dakika
        await ctx.send(f"Ship için Mesaj gönderme zamanı ayarlandı: {SHIP_TARGET_HOUR:02}:{SHIP_TARGET_MINUTE:02}")
    else:
        await ctx.send("Geçersiz saat veya dakika! 0-23 saat, 0-59 dakika olmalı.")

# Yönetici olmayan kullanıcılar için özel hata mesajı
@shipzaman.error
async def shipzaman_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için yönetici yetkisine sahip olmalısın!")



@bot.command()
async def log(ctx):
    try:
        with open("kisi_log.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            await ctx.send("📂 Log dosyası boş.")
            return

        mesajlar = []
        for tarih, kayit in data.items():
            giren = kayit.get("giren", 0)
            cikan = kayit.get("cikan", 0)
            mesajlar.append(f"📅 {tarih} → Katılan: {giren} | Çıkan: {cikan}")

        # Discord mesaj limiti (2000 karakter) var, ona göre parçala
        chunk = ""
        for satir in mesajlar:
            if len(chunk) + len(satir) + 1 > 2000:
                await ctx.send(chunk)
                chunk = satir + "\n"
            else:
                chunk += satir + "\n"

        if chunk:
            await ctx.send(chunk)

    except FileNotFoundError:
        await ctx.send("❌ Log dosyası bulunamadı.")
    except json.JSONDecodeError:
        await ctx.send("⚠️ Log dosyası bozuk veya boş.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def topluban(ctx, *user_ids: int):
    banned = []
    for uid in user_ids:
        try:
            user = await bot.fetch_user(uid)
            await ctx.guild.ban(user, reason="Toplu ban")
            banned.append(str(uid))
        except Exception as e:
            await ctx.send(f"{uid} banlanamadı: {e}")
    await ctx.send(f"Banlananlar: {', '.join(banned)}")

channel_limits = {}


@bot.command()
@commands.is_owner()
async def mesajgonder(ctx, *, mesaj: str): #seçilen kanala belirlenen mesaj gönderir. Komutu kullanan kişinin mesajını siler.
    await ctx.message.delete()  # Komutu kullanan kişinin mesajını sil
    await ctx.send(mesaj)  # Belirtilen mesajı gönder




@bot.event
async def on_message(message):
    # Botun kendi mesajlarını kontrol etme
    if message.author.bot:
        return  

    # 1) Selam cevabı
    if message.content.lower() in ["sa", "selam", "selamlar"]:
        await message.channel.send(f"**Aleyküm selam {message.author.mention}!  Nasılsın? <:selam:1384247246924677313>**")

        def check(m):
            return m.author == message.author and m.channel == message.channel and m.content.lower() in ["iyiyim sen", "iyi sen", "iyidir sen", "hamdolsun sen"]

        try:
            reply = await bot.wait_for("message", timeout=20.0, check=check)
            await message.channel.send(f"{message.author.mention} **Teşekkürler, iyi olmana sevindim! 😄**")
        except asyncio.TimeoutError:
            # Eğer kullanıcı 20 saniye içinde cevap vermezse bir şey yapma
            pass
    
    # Kanal için limit varsa uygula
    if message.channel.id in channel_limits:
        limit = channel_limits[message.channel.id]

        if len(message.content) > limit:
            if not message.author.guild_permissions.manage_messages:  
                await message.delete()
                try:
                    await message.author.send(
                        f"Mesajın silindi! Bu kanalda limit **{limit}** karakter."
                    )
                except:
                    await message.channel.send(
                        f"{message.author.mention} mesajın çok uzun olduğu için silindi! (Limit: {limit})"
                    )

    # Komutların çalışabilmesi için
    await bot.process_commands(message)



# Bot açılırken kaydedilmiş veriyi yükle
if os.path.exists("limits.json"):
    with open("limits.json", "r", encoding="utf-8") as f:
        channel_limits = json.load(f)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def limit(ctx, karakter: int):
    channel_limits[str(ctx.channel.id)] = karakter
    with open("limits.json", "w", encoding="utf-8") as f:
        json.dump(channel_limits, f, ensure_ascii=False, indent=4)
    await ctx.send(f"✅ Bu kanal için karakter limiti **{karakter}** olarak ayarlandı.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def limitkapat(ctx):
    if str(ctx.channel.id) in channel_limits:
        del channel_limits[str(ctx.channel.id)]
        with open("limits.json", "w", encoding="utf-8") as f:
            json.dump(channel_limits, f, ensure_ascii=False, indent=4)
        await ctx.send("❌ Bu kanal için karakter limiti kaldırıldı.")
    else:
        await ctx.send("Bu kanalda zaten limit ayarlı değil.")
        
DATA_FILE = "kisi_log.json"

def load_data():
    global girenkisisayisi, cikankisisayisi
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Dosya bozuksa temizle
        data = {}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    today = date.today().isoformat()
    if today in data:
        girenkisisayisi = data[today].get("giren", 0)
        cikankisisayisi = data[today].get("cikan", 0)



def save_data():
    today = date.today().isoformat()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    if today not in data:
        data[today] = {"giren": 0, "cikan": 0}

    data[today]["giren"] = girenkisisayisi
    data[today]["cikan"] = cikankisisayisi

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@bot.event
async def on_member_join(member):
    global girenkisisayisi
    if member.bot:
        return
    channel = bot.get_channel(1382742472207368192)
    await channel.send(f"{member.mention} aramıza katıldı! Hoş geldin! <:selam:1384247246924677313>")

    girenkisisayisi += 1
    save_data()


@bot.event
async def on_member_remove(member):
    global cikankisisayisi
    cikankisisayisi += 1
    save_data()


@tasks.loop(seconds=30)
async def kisisayisisifirla():
    global girenkisisayisi, cikankisisayisi
    now = datetime.utcnow() + timedelta(hours=3)
    if now.hour == 0 and now.minute == 0:
        girenkisisayisi = 0
        cikankisisayisi = 0
        save_data()
        await asyncio.sleep(60)  # Aynı dakika içinde tekrar çalışmaması için


@tasks.loop(seconds=30)
async def send_daily_report():
    now = datetime.utcnow() + timedelta(hours=3)
    if now.hour == 23 and now.minute == 0:
        today = date.today().isoformat()
        channel = bot.get_channel(123456789012345678)  # rapor kanalı
        if channel:
            await channel.send(f"Bugün ({today}) katılan: {girenkisisayisi} | çıkan: {cikankisisayisi}")
            await asyncio.sleep(60)
            save_data()
        await asyncio.sleep(60)  # Aynı dakika içinde tekrar çalışmaması için


@bot.command()
@commands.is_owner()
async def raporsifirla(ctx):
    global girenkisisayisi, cikankisisayisi
    girenkisisayisi = 0
    cikankisisayisi = 0
    save_data()
    await ctx.send("Günlük rapor sıfırlandı ve dosyaya kaydedildi.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def raporver(ctx):
    global girenkisisayisi, cikankisisayisi
    today = date.today().isoformat()
    await ctx.send(f"Bugün ({today}) katılan: {girenkisisayisi} | çıkan: {cikankisisayisi}")


@bot.event
async def on_ready():
    print(f"{bot.user} giriş yaptı ✅")
    await load_extensions()
    rastgele_anime_gonder.start()
    gununhantigonder.start()
    print(f"Bot {len(bot.guilds)} sunucuda bulunuyor:")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    send_daily_report.start()
    kisisayisisifirla.start()
    load_data()
    save_data()  # JSON dosyası artık sıfır değerlerle oluşacak

def kanalbulunamadi(ctx):
    return ctx.send("Kanal bulunamadı. Lütfen geçerli bir kanal ID'si girin.")

bot.command()
async def help(ctx):
    if not await bot.is_owner(ctx.author):
        return
    
    help_text = "**Bot Komutları:**\n\n"
    
    for cog_name, cog in bot.cogs.items():
        commands_list = [cmd.name for cmd in cog.get_commands() if not cmd.hidden]
        if commands_list:
            help_text += f"**{cog_name}:**\n"
            help_text += ", ".join(commands_list) + "\n\n"
    
    # Cog'a ait olmayan komutlar
    no_cog_commands = [cmd.name for cmd in bot.commands if cmd.cog is None and not cmd.hidden]
    if no_cog_commands:
        help_text += "**Diğer Komutlar:**\n"
        help_text += ", ".join(no_cog_commands) + "\n\n"
    
    await ctx.send(help_text)

@tasks.loop(seconds=30)
async def gununhantigonder():
    channel = bot.get_channel(gununhanti_kanalid)
    if channel is None:
        print(f"Kanal bulunamadı: {gununhanti_kanalid}")
        return
    print("Task loop Çalıştı Gunun Hanti")
    now = datetime.utcnow() + timedelta(hours=3)
    print(f"Şu an saat: {now.hour}, dakika: {now.minute}")
    print(f"Hedef saat: {Gununhanti_TARGET_HOUR}, hedef dakika: {Gununhanti_TARGET_MINUTE}")
    if now.hour == 23 and now.minute == 0: #Her gün saat 23 de sunucudaki kişi sayısı kanala gönderilecek
        print("Günün Hantı Gönderim zamanı geldi!")
        await channel.send(f"Bugün sunucumuzda toplam {channel.guild.member_count}")
        await asyncio.sleep(60) 
    else:
        print("Henüz zamanı değil")  # if içine girmezse bunu yazdırır
    
        
@bot.command()
@commands.is_owner()
async def gununhanti(ctx):
    channel = bot.get_channel(gununhanti_kanalid)
    await channel.send(f"Bugün sunucumuzda toplam {channel.guild.member_count} kişi var! <:selam:1384247246924677313>")


@tasks.loop(seconds=30)
async def rastgele_anime_gonder():
    channel = bot.get_channel(kanalid)
    if channel is None:
        print(f"Kanal bulunamadı: {kanalid}")
        return
    print("Task loop Çalıştı")

    now = datetime.utcnow() + timedelta(hours=3)
    print(f"Şu an saat: {now.hour}, dakika: {now.minute}")
    print(f"Hedef saat: {TARGET_HOUR}, hedef dakika: {TARGET_MINUTE}")
    print(now.hour, now.minute)
    if now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE:
        print("Gönderim zamanı geldi!")
        anime = get_rastgele_anime()
        puan = anime['score'] if anime['score'] is not None else 'Veri yok'
        rank = anime['rank'] if anime['rank'] is not None else 'Veri yok'
        bolumsayisi = anime['episodes'] if anime['episodes'] is not None else 'Veri yok'
        
        description = f"""
        ⭐ Puan: {puan}
        🎬 Sıralama: {rank}
        📺 Bölüm Sayısı: {bolumsayisi}
        <@&1406948083912278088>

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
    else:
        print("Henüz zamanı değil")  # if içine girmezse bunu yazdırır

@bot.command()
@commands.is_owner()
async def embedyaz(ctx):
    anime = get_rastgele_anime()
    puan = anime['score'] if anime['score'] is not None else 'Not available'
    rank = anime['rank'] if anime['rank'] is not None else 'Not available'
    bolumsayisi = anime['episodes'] if anime['episodes'] is not None else 'Not available'

    description = f"""
    ⭐ Puan: {puan}
    🎬 Sıralama: {rank}
    📺 Bölüm Sayısı: {bolumsayisi}
    <@&1406948083912278088>
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

def merge_images(url1, url2, filename="ship.png"):

    img1 = Image.open(BytesIO(requests.get(url1).content))
    img2 = Image.open(BytesIO(requests.get(url2).content))

    # Aynı boyuta getir
    img1 = img1.resize((450, 700))
    img2 = img2.resize((450, 700))

    # Yan yana birleştir (toplam 900x700)
    merged = Image.new("RGB", (900, 700))
    merged.paste(img1, (0, 0))
    merged.paste(img2, (450, 0))

    merged.save(filename)
    return filename


def get_rastgele_karakter():
    url = "https://api.jikan.moe/v4/random/characters"

    while True:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            karakter = data['data']

            # Karakterin adı varsa çık
            if karakter.get('name'):
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
        'about': karakter.get('about', 'Bilgi yok'),
        'nicknames': karakter.get('nicknames', []),
        'image_url': karakter['images']['jpg']['image_url']
    }

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
bot.run(TOKEN)