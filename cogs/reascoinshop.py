import discord
from discord.ext import commands
import sqlite3
import asyncio

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_inventory_table()
        
        # Market kategorileri ve ürünleri
        self.market_items = {
            "renkler": {
                "emoji": "🎨",
                "items": {
                    "mavi renk": {
                        "name": "Mavi Rol",
                        "price": 100,
                        "role_id": 1417903608225333469,
                        "description": "Mavi renkli özel rol",
                        "item_type": "color_role"
                    },
                    "yeşil renk": {
                        "name": "Yeşil Rol",
                        "price": 100,
                        "role_id": 1418320278827827322,
                        "description": "Yeşil renkli özel rol",
                        "item_type": "color_role"
                    },
                    "pembe renk": {
                        "name": "Pembe Rol",
                        "price": 100,
                        "role_id": 1405194610078388224,
                        "description": "Pembe renkli özel rol",
                        "item_type": "color_role"
                    }
                }
            }
        }

    def setup_inventory_table(self):
        """Envanter tablosunu oluştur"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_key TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                role_id INTEGER,
                purchased_date TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0,
                UNIQUE(user_id, item_key)
            )
        ''')
        
        conn.commit()
        conn.close()

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

    def add_to_inventory(self, user_id, item_key, item_data):
        """Envatere ürün ekle"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO user_inventory 
            (user_id, item_key, item_name, item_type, role_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, item_key, item_data['name'], 
              item_data.get('item_type', 'unknown'), 
              item_data.get('role_id')))
        
        conn.commit()
        conn.close()

    def get_user_inventory(self, user_id, item_type=None):
        """Kullanıcının envanterini getir"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if item_type:
            cursor.execute('''
                SELECT item_key, item_name, item_type, role_id, is_active 
                FROM user_inventory 
                WHERE user_id = ? AND item_type = ?
                ORDER BY purchased_date DESC
            ''', (user_id, item_type))
        else:
            cursor.execute('''
                SELECT item_key, item_name, item_type, role_id, is_active 
                FROM user_inventory 
                WHERE user_id = ?
                ORDER BY item_type, purchased_date DESC
            ''', (user_id,))
        
        result = cursor.fetchall()
        conn.close()
        
        return result

    def update_active_item(self, user_id, item_key, item_type):
        """Aktif öğeyi güncelle (aynı türdeki diğerlerini pasif yap)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Önce aynı türdeki tüm öğeleri pasif yap
        cursor.execute('''
            UPDATE user_inventory 
            SET is_active = 0 
            WHERE user_id = ? AND item_type = ?
        ''', (user_id, item_type))
        
        # Seçilen öğeyi aktif yap
        cursor.execute('''
            UPDATE user_inventory 
            SET is_active = 1 
            WHERE user_id = ? AND item_key = ?
        ''', (user_id, item_key))
        
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
            
            embed.set_footer(text="Kullanım: r!market <kategori> | r!envanter ile envanterinizi görün")
            
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

    @commands.command(name='market', aliases=['m'])
    async def market(self, ctx, kategori=None):
        """Market komutunu göster"""
        embed = self.create_market_embed(kategori)
        
        if embed is None:
            await ctx.send("❌ Böyle bir kategori bulunamadı!")
            return
            
        await ctx.send(embed=embed)

    @commands.command(name='satinal', aliases=['buy', 'al'])
    async def buy_item(self, ctx, *, item_name=None):
        """Ürün satın alma"""
        if item_name is None:
            await ctx.send("❌ Satın almak istediğiniz ürünü belirtiniz! Örnek: `r!satinal mavi renk`")
            return

        # Ürünü bul
        found_item = None
        found_key = None
        found_category = None
        
        for category, cat_data in self.market_items.items():
            if item_name.lower() in cat_data['items']:
                found_item = cat_data['items'][item_name.lower()]
                found_key = item_name.lower()
                found_category = category
                break
        
        if found_item is None:
            await ctx.send("❌ Böyle bir ürün bulunamadı! `r!market` ile mevcut ürünleri görebilirsiniz.")
            return

        user_id = ctx.author.id
        
        # Envaterde var mı kontrol et
        inventory = self.get_user_inventory(user_id)
        for inv_item in inventory:
            if inv_item[0] == found_key:  # item_key kontrolü
                await ctx.send("❌ Bu ürün zaten envanterinizde var! `r!envanter` komutuyla kontrol edebilirsiniz.")
                return

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

        # Satın alma onayı
        embed = discord.Embed(
            title="🛒 Satın Alma Onayı",
            description=f"**{found_item['name']}** satın almak istediğinizden emin misiniz?",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Fiyat", value=f"{found_item['price']} Reas Coin", inline=True)
        embed.add_field(name="💳 Mevcut Bakiye", value=f"{user_coins} Reas Coin", inline=True)
        embed.add_field(name="💳 Kalan Bakiye", value=f"{user_coins - found_item['price']} Reas Coin", inline=True)
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
                # Son kontrol
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

                # Envatere ekle
                self.add_to_inventory(user_id, found_key, found_item)

                embed = discord.Embed(
                    title="✅ Satın Alma Başarılı!",
                    description=f"**{found_item['name']}** envanterinize eklendi!\n`r!envanter` komutuyla görüntüleyip kullanabilirsiniz.",
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

    @commands.command(name='envanter', aliases=['inventory', 'inv'])
    async def inventory(self, ctx, kategori=None):
        """Envanteri göster"""
        user_id = ctx.author.id
        
        if kategori == "renkler" or kategori == "renk":
            inventory = self.get_user_inventory(user_id, "color_role")
            title = "🎨 Renk Envanteriniz"
        else:
            inventory = self.get_user_inventory(user_id)
            title = "📦 Envanteriniz"
        
        if not inventory:
            embed = discord.Embed(
                title=title,
                description="Envanteriniz boş! `r!market` ile ürün satın alabilirsiniz.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=title,
            description="Sahip olduğunuz ürünler:",
            color=discord.Color.blue()
        )

        color_items = []
        other_items = []
        
        for item in inventory:
            item_key, item_name, item_type, role_id, is_active = item
            status = "🟢 Aktif" if is_active else "⚪ Pasif"
            
            if item_type == "color_role":
                color_items.append(f"{status} **{item_name}**\n`r!kullan {item_key}`")
            else:
                other_items.append(f"{status} **{item_name}**\n`r!kullan {item_key}`")

        if color_items:
            embed.add_field(
                name="🎨 Renkler",
                value="\n\n".join(color_items),
                inline=False
            )
        
        if other_items:
            embed.add_field(
                name="📦 Diğer Ürünler",
                value="\n\n".join(other_items),
                inline=False
            )

        embed.set_footer(text="Kullanım: r!kullan <ürün_adı> ile ürünü aktif yapın")
        await ctx.send(embed=embed)

    @commands.command(name='kullan', aliases=['use', 'equip'])
    async def use_item(self, ctx, *, item_name=None):
        """Envaterdeki ürünü kullan/aktif et"""
        if item_name is None:
            await ctx.send("❌ Kullanmak istediğiniz ürünü belirtiniz! Örnek: `r!kullan mavi renk`")
            return

        user_id = ctx.author.id
        inventory = self.get_user_inventory(user_id)
        
        # Ürünü envaterde bul
        found_item = None
        for inv_item in inventory:
            item_key, item_name_db, item_type, role_id, is_active = inv_item
            if item_name.lower() == item_key.lower() or item_name.lower() in item_name_db.lower():
                found_item = inv_item
                break
        
        if found_item is None:
            await ctx.send("❌ Bu ürün envanterinizde bulunamadı! `r!envanter` ile kontrol edin.")
            return

        item_key, item_name_db, item_type, role_id, is_active = found_item

        if is_active:
            await ctx.send("❌ Bu ürün zaten aktif durumda!")
            return

        # Renk rolü işlemi
        if item_type == "color_role":
            try:
                # Önce mevcut aktif renk rollerini kaldır
                current_inventory = self.get_user_inventory(user_id, "color_role")
                for inv_item in current_inventory:
                    _, _, _, old_role_id, old_is_active = inv_item
                    if old_is_active and old_role_id:
                        old_role = ctx.guild.get_role(old_role_id)
                        if old_role and old_role in ctx.author.roles:
                            await ctx.author.remove_roles(old_role, reason="Renk değiştirme")

                # Yeni rolü ver
                new_role = ctx.guild.get_role(role_id)
                if new_role is None:
                    await ctx.send("❌ Bu rol sunucuda bulunamadı!")
                    return
                
                await ctx.author.add_roles(new_role, reason="Envanter kullanımı")
                
                # Veritabanını güncelle
                self.update_active_item(user_id, item_key, item_type)
                
                embed = discord.Embed(
                    title="✅ Renk Değiştirildi!",
                    description=f"**{item_name_db}** artık aktif!",
                    color=new_role.color if new_role.color != discord.Color.default() else discord.Color.green()
                )
                await ctx.send(embed=embed)

            except discord.Forbidden:
                await ctx.send("❌ Bu rolü verme yetkim yok!")
                return
        else:
            # Diğer ürün türleri için genişletilebilir
            self.update_active_item(user_id, item_key, item_type)
            embed = discord.Embed(
                title="✅ Ürün Aktif!",
                description=f"**{item_name_db}** artık aktif!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

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