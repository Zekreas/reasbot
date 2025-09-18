import discord
from discord.ext import commands
import sqlite3
import asyncio

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "reas.db"
        
        # Market ürünleri - şimdilik sadece renkler
        self.color_roles = {
            "mavi": {
                "name": "🔵 Mavi",
                "price": 100,
                "role_id": 1417903608225333469,
                "emoji": "🔵"
            }
            # Daha fazla renk buraya eklenecek
        }
    
    def get_user_coins(self, user_id):
        """Kullanıcının coin miktarını al"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT reas_coin FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def update_user_coins(self, user_id, new_amount):
        """Kullanıcının coin miktarını güncelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""INSERT INTO users (user_id, reas_coin, xp, voicehour) 
                         VALUES (?, ?, 0, 0) 
                         ON CONFLICT(user_id) DO UPDATE SET reas_coin = ?""", 
                      (user_id, new_amount, new_amount))
        conn.commit()
        conn.close()
    
    @commands.slash_command(name="market", description="Marketi görüntüle")
    async def market(self, ctx):
        embed = discord.Embed(
            title="🛒 Reas Market",
            description="Reas Coin karşılığında ürün satın alabilirsin!",
            color=discord.Color.blue()
        )
        
        user_coins = self.get_user_coins(ctx.author.id)
        embed.add_field(
            name="💰 Bakiyen", 
            value=f"{user_coins} Reas Coin", 
            inline=False
        )
        
        # Renk kategorisi
        color_text = ""
        for key, item in self.color_roles.items():
            color_text += f"{item['emoji']} **{item['name']}** - {item['price']} Coin\n"
        
        embed.add_field(
            name="🎨 Renkli Roller", 
            value=color_text, 
            inline=False
        )
        
        embed.add_field(
            name="📝 Nasıl Satın Alırım?", 
            value="`/satinal <kategori> <ürün>` komutunu kullan\nÖrnek: `/satinal renk mavi`", 
            inline=False
        )
        
        embed.set_footer(text="Daha fazla ürün yakında gelecek!")
        await ctx.respond(embed=embed)
    
    @commands.slash_command(name="satinal", description="Market'ten ürün satın al")
    async def buy_item(self, ctx, kategori: str, urun: str):
        user_coins = self.get_user_coins(ctx.author.id)
        
        if kategori.lower() in ["renk", "renkler", "color"]:
            if urun.lower() in self.color_roles:
                item = self.color_roles[urun.lower()]
                
                # Yeterli coin kontrolü
                if user_coins < item["price"]:
                    embed = discord.Embed(
                        title="❌ Yetersiz Bakiye",
                        description=f"Bu ürün için **{item['price']} Reas Coin** gerekli.\nSenin bakiyen: **{user_coins} Reas Coin**",
                        color=discord.Color.red()
                    )
                    await ctx.respond(embed=embed)
                    return
                
                # Rolü zaten var mı kontrolü
                role = discord.utils.get(ctx.guild.roles, id=item["role_id"])
                if role in ctx.author.roles:
                    embed = discord.Embed(
                        title="⚠️ Zaten Sahipsin",
                        description=f"**{item['name']}** rolüne zaten sahipsin!",
                        color=discord.Color.orange()
                    )
                    await ctx.respond(embed=embed)
                    return
                
                # Satın alma onayı
                embed = discord.Embed(
                    title="🛒 Satın Alma Onayı",
                    description=f"**{item['name']}** rolünü **{item['price']} Reas Coin** karşılığında satın almak istediğinden emin misin?",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Mevcut Bakiyen", value=f"{user_coins} Reas Coin", inline=True)
                embed.add_field(name="Kalan Bakiyen", value=f"{user_coins - item['price']} Reas Coin", inline=True)
                
                view = BuyConfirmView(self, ctx.author.id, item, user_coins)
                await ctx.respond(embed=embed, view=view)
                
            else:
                embed = discord.Embed(
                    title="❌ Ürün Bulunamadı",
                    description=f"**{urun}** adında bir renk bulunamadı.\nMevcut renkler: `mavi`",
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Kategori Bulunamadı",
                description=f"**{kategori}** adında bir kategori bulunamadı.\nMevcut kategoriler: `renk`",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)

class BuyConfirmView(discord.ui.View):
    def __init__(self, market_cog, user_id, item, user_coins):
        super().__init__(timeout=30)
        self.market_cog = market_cog
        self.user_id = user_id
        self.item = item
        self.user_coins = user_coins
    
    @discord.ui.button(label="✅ Satın Al", style=discord.ButtonStyle.success)
    async def confirm_buy(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bu buton sadece komutu kullanan kişi için!", ephemeral=True)
            return
        
        # Rolü ver
        role = discord.utils.get(interaction.guild.roles, id=self.item["role_id"])
        if role:
            try:
                await interaction.user.add_roles(role)
                
                # Coini düş
                new_balance = self.user_coins - self.item["price"]
                self.market_cog.update_user_coins(self.user_id, new_balance)
                
                embed = discord.Embed(
                    title="✅ Satın Alma Başarılı!",
                    description=f"**{self.item['name']}** rolü başarıyla satın alındı!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Harcanan", value=f"{self.item['price']} Reas Coin", inline=True)
                embed.add_field(name="Kalan Bakiyen", value=f"{new_balance} Reas Coin", inline=True)
                
                await interaction.response.edit_message(embed=embed, view=None)
                
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Yetki Hatası",
                    description="Rolü verirken bir hata oluştu. Botun yeterli yetkisi olmayabilir.",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="❌ Rol Bulunamadı",
                description="Rol sunucuda bulunamadı. Lütfen yönetici ile iletişime geçin.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ İptal", style=discord.ButtonStyle.danger)
    async def cancel_buy(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bu buton sadece komutu kullanan kişi için!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Satın Alma İptal Edildi",
            description="Satın alma işlemi iptal edildi.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        # Zaman aşımında tüm butonları devre dışı bırak
        for item in self.children:
            item.disabled = True

def setup(bot):
    bot.add_cog(Market(bot))