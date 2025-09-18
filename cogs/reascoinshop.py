import discord
from discord.ext import commands
import sqlite3
import asyncio

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Market kategorileri ve ürünleri
        self.market_items = {
            "renkler": {
                "emoji": "🎨",
                "items": {
                    "mavi renk": {
                        "name": "Mavi Rol",
                        "price": 100,
                        "role_id": 1417903608225333469,
                    },
                    # Buraya daha fazla renk ekleyebilirsiniz
                    "yeşil renk": {
                        "name": "Yeşil Rol",
                        "price": 100,
                        "role_id": 1418320278827827322,
                    },
                    "pembe renk": {
                        "name": "Pembe Rol",
                        "price": 100,
                        "role_id": 1405194610078388224,
                    }
                }
            }
            # Buraya yeni kategoriler ekleyebilirsiniz
        }


    def get_db_connection(self):
        """Veritabanı bağlantısı"""
        return sqlite3.connect('reas.db')

    def get_user_coins(self, user_id):
        """Kullanıcının coin miktarını getir"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT reas_coin FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0

    def update_user_coins(self, user_id, new_amount):
        """Kullanıcının coin miktarını güncelle"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, reas_coin, xp, voicehour, last_daily, voice_daily_date, voice_daily_coins)
            VALUES (?, ?, 
                    COALESCE((SELECT xp FROM users WHERE user_id = ?), 0),
                    COALESCE((SELECT voicehour FROM users WHERE user_id = ?), 0),
                    COALESCE((SELECT last_daily FROM users WHERE user_id = ?), '0'),
                    COALESCE((SELECT voice_daily_date FROM users WHERE user_id = ?), '0'),
                    COALESCE((SELECT voice_daily_coins FROM users WHERE user_id = ?), 0))
        """, (user_id, new_amount, user_id, user_id, user_id, user_id, user_id))
        
        conn.commit()
        conn.close()

    def create_market_embed(self, category=None):
        """Market embed'i oluştur"""
        if category is None:
            # Ana market sayfası
            embed = discord.Embed(
                title="🛒 Reas Market",
                description="Reas coin'lerinizi harcamak için kategorileri görüntüleyin!",
                color=discord.Color.gold()
            )
            
            for cat_name, cat_data in self.market_items.items():
                embed.add_field(
                    name=f"{cat_data['emoji']} {cat_name.title()}",
                    value=f"`r!market {cat_name}` ile görüntüle",
                    inline=True
                )
            
            embed.set_footer(text="Kullanım: r!market <kategori>")
            
        else:
            # Kategori sayfası
            if category not in self.market_items:
                return None
                
            cat_data = self.market_items[category]
            embed = discord.Embed(
                title=f"{cat_data['emoji']} {category.title()} Market",
                description="Aşağıdaki ürünlerden satın alabilirsiniz:",
                color=discord.Color.blue()
            )
            
            for item_key, item_data in cat_data['items'].items():
                embed.add_field(
                    name=f"{item_data['name']}",
                    value=f"💰 Fiyat: {item_data['price']} Reas Coin\n📝 {item_data['description']}\n`r!satinal {item_key}`",
                    inline=False
                )
            
            embed.set_footer(text="Kullanım: r!satinal <ürün_adı>")
        
        return embed

    def get_color_roles(self):
        """Renk rollerinin ID'lerini döndür"""
        color_roles = []
        if "renkler" in self.market_items:
            for item_data in self.market_items["renkler"]["items"].values():
                if "role_id" in item_data:
                    color_roles.append(item_data["role_id"])
        return color_roles

    async def remove_color_roles(self, member):
        """Kullanıcının sahip olduğu tüm renk rollerini kaldır"""
        color_role_ids = self.get_color_roles()
        roles_to_remove = []
        
        for role in member.roles:
            if role.id in color_role_ids:
                roles_to_remove.append(role)
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Yeni renk rolü için eski renk kaldırıldı")
            return [role.name for role in roles_to_remove]
        return []

    @commands.command(name='market', aliases=['m'])
    async def market(self, ctx, kategori=None):
        """Market komutunu göster"""
        embed = self.create_market_embed(kategori)
        
        if embed is None:
            await ctx.send("❌ Böyle bir kategori bulunamadı!")
            return
            
        await ctx.send(embed=embed)

    @commands.command(name='satinal', aliases=['buy', 'al'])
    async def buy_item(self, ctx, item_name=None):
        """Ürün satın alma"""
        if item_name is None:
            await ctx.send("❌ Satın almak istediğiniz ürünü belirtiniz! Örnek: `r!satinal mavi`")
            return

        # Ürünü bul
        found_item = None
        found_category = None
        
        for category, cat_data in self.market_items.items():
            if item_name.lower() in cat_data['items']:
                found_item = cat_data['items'][item_name.lower()]
                found_category = category
                break
        
        if found_item is None:
            await ctx.send("❌ Böyle bir ürün bulunamadı! `r!market` ile mevcut ürünleri görebilirsiniz.")
            return

        user_id = ctx.author.id
        user_coins = self.get_user_coins(user_id)
        
        # Coin kontrolü
        if user_coins < found_item['price']:
            embed = discord.Embed(
                title="❌ Yetersiz Bakiye",
                description=f"Bu ürün için **{found_item['price']} Reas Coin** gerekiyor.\nSizin bakiyeniz: **{user_coins} Reas Coin**",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Rol kontrolü (sadece rol ürünleri için)
        removed_roles = []
        if 'role_id' in found_item:
            role = ctx.guild.get_role(found_item['role_id'])
            if role is None:
                await ctx.send("❌ Bu rol sunucuda bulunamadı!")
                return
            
            if role in ctx.author.roles:
                await ctx.send("❌ Bu role zaten sahipsiniz!")
                return
            
            # Eğer renk kategorisindeyse, mevcut renk rollerini kaldır
            if found_category == "renkler":
                removed_roles = await self.remove_color_roles(ctx.author)

        # Satın alma onayı
        embed = discord.Embed(
            title="🛒 Satın Alma Onayı",
            description=f"**{found_item['name']}** satın almak istediğinizden emin misiniz?",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Fiyat", value=f"{found_item['price']} Reas Coin", inline=True)
        embed.add_field(name="💳 Mevcut Bakiye", value=f"{user_coins} Reas Coin", inline=True)
        embed.add_field(name="💳 Kalan Bakiye", value=f"{user_coins - found_item['price']} Reas Coin", inline=True)
        
        if removed_roles and found_category == "renkler":
            embed.add_field(
                name="⚠️ Uyarı", 
                value=f"Mevcut renk rolünüz ({', '.join(removed_roles)}) kaldırılacak!", 
                inline=False
            )
        
        embed.set_footer(text="✅ ile onaylayın, ❌ ile iptal edin (30 saniye)")

        message = await ctx.send(embed=embed)
        await message.add_reaction('✅')
        await message.add_reaction('❌')

        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ['✅', '❌'] and 
                   reaction.message.id == message.id)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '❌':
                embed = discord.Embed(
                    title="❌ İptal Edildi",
                    description="Satın alma işlemi iptal edildi.",
                    color=discord.Color.red()
                )
                await message.edit(embed=embed)
                return

            elif str(reaction.emoji) == '✅':
                # Son kontrol (eşzamanlılık için)
                current_coins = self.get_user_coins(user_id)
                if current_coins < found_item['price']:
                    embed = discord.Embed(
                        title="❌ Yetersiz Bakiye",
                        description="Satın alma sırasında bakiyeniz değişti!",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed)
                    return

                # Coin'leri düş
                new_balance = current_coins - found_item['price']
                self.update_user_coins(user_id, new_balance)

                # Rol ver (eğer rol ürünüyse)
                success = True
                if 'role_id' in found_item:
                    try:
                        # Renk kategorisindeyse önce eski renk rollerini kaldır
                        if found_category == "renkler":
                            await self.remove_color_roles(ctx.author)
                        
                        role = ctx.guild.get_role(found_item['role_id'])
                        await ctx.author.add_roles(role, reason="Market satın alma")
                    except discord.Forbidden:
                        success = False
                        # Coin'leri geri ver
                        self.update_user_coins(user_id, current_coins)
                        embed = discord.Embed(
                            title="❌ Yetki Hatası",
                            description="Bu rolü verme yetkim yok! Coin'leriniz iade edildi.",
                            color=discord.Color.red()
                        )
                        await message.edit(embed=embed)
                        return

                if success:
                    embed = discord.Embed(
                        title="✅ Satın Alma Başarılı!",
                        description=f"**{found_item['name']}** başarıyla satın alındı!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="💰 Ödenen", value=f"{found_item['price']} Reas Coin", inline=True)
                    embed.add_field(name="💳 Kalan Bakiye", value=f"{new_balance} Reas Coin", inline=True)
                    await message.edit(embed=embed)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Zaman Aşımı",
                description="30 saniye içinde yanıt verilmedi, işlem iptal edildi.",
                color=discord.Color.orange()
            )
            await message.edit(embed=embed)

    @commands.command(name='coin', aliases=['bal', 'balance', 'bakiye'])
    async def balance(self, ctx, user: discord.Member = None):
        """Coin bakiyesini göster"""
        if user is None:
            user = ctx.author
            
        user_coins = self.get_user_coins(user.id)
        
        embed = discord.Embed(
            title=f"💰 {user.display_name} - Bakiye",
            description=f"**{user_coins} Reas Coin**",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Market(bot))