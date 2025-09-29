import discord
from discord.ext import commands, tasks
import sqlite3
import aiosqlite
import asyncio
from datetime import date, datetime, timedelta
from cogs.reascoinshop import check_channel
import random

class Yardim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"

    @commands.command(name="yardım", aliases=["yardim", "help_user"])
    @check_channel()
    async def yardim(self, ctx):
        """Üyeler için mevcut komutları gösterir"""
        
        embed = discord.Embed(
            title="🤖 Reas Bot - Kullanıcı Komutları",
            description="Merhaba! İşte kullanabileceğin tüm komutlar:",
            color=discord.Color.blue()
        )
        
        # Coin Sistemi
        embed.add_field(
            name="💰 Coin Sistemi",
            value=(
                "`r!daily` - Günlük coin ödülünü al (15-60 coin, %5 şans 100 coin)\n"
                "`r!coin` - Coin bakiyeni görüntüle\n"
                "`r!coin @kullanıcı` - Başka kullanıcının bakiyesini gör\n"
                "`r!top` - Coin sıralamasını görüntüle\n"
                "`r!coinhaklarim` - Günlük coin limitlerini kontrol et"
            ),
            inline=False
        )
        
        # Market Sistemi
        embed.add_field(
            name="🛒 Market Sistemi",
            value=(
                "`r!market` - Ana market sayfasını görüntüle\n"
                "`r!market renkler` - Renk rolü kategorisini gör\n"
                "`r!market roller` - Özel rol kategorisini gör\n"
                "`r!satinal <ürün>` - Ürün satın al (örn: r!satinal mavi renk)\n"
                "`r!envanter` - Tüm envanterini görüntüle\n"
                "`r!envanter renkler` - Sadece renk envanterini gör\n"
                "`r!kullan <ürün>` - Envaterdeki ürünü aktif et"
            ),
            inline=False
        )
        
        # Aktivite ve İstatistikler
        embed.add_field(
            name="📊 Aktivite & İstatistikler",
            value=(
                "`r!profil` - Kendi profilini görüntüle\n"
                "`r!profil @kullanıcı` - Başka kullanıcının profilini gör\n"
                "`r!voicetop` - Ses kanalı sıralamasını görüntüle\n"
                "`r!ayliksiralamamesaj` - Aylık mesaj sıralamasını gör"
            ),
            inline=False
        )
        
        # Genel Bilgiler
        embed.add_field(
            name="ℹ️ Önemli Bilgiler",
            value=(
                "• Coin kazanma yolları:\n"
                "  - Mesaj atarak (30 saniye cooldown, 1 coin)\n"
                "  - Ses kanalında durarak (2 dakikada 1 coin, günlük max 160)\n"
                "  - Günlük ödül komutu\n\n"
                "• Çoğu komut sadece <#1418328370915184730> kanalında çalışır\n"
                "• Market'ten aldığın renkler envatere eklenir\n"
                "• Diğer ürünler direkt uygulanır"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bu komutlar sadece üyeler içindir. Daha fazla bilgi için komutları deneyin!")
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await ctx.send(embed=embed)

    
async def setup(bot):
    await bot.add_cog(Yardim(bot))
