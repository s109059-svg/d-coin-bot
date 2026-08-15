import os
import json
import discord
from discord import app_commands
from discord.ext import commands

# =========================
# 基本設定
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

LOG_CHANNEL_ID = 1538123620193280021

DATA_FILE = "data.json"


# =========================
# D幣商店
# =========================

SHOP_ITEMS = {
    "skinbox": {
        "name": "🎁 皮膚箱 ×1",
        "price": 5000
    },

    "title": {
        "name": "🏆 限定稱號",
        "price": 10000
    },

    "rich": {
        "name": "💰 有錢人身分組",
        "price": 50000
    }
}


# =========================
# 資料庫
# =========================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except:
        return {}


def save_data():

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


data = load_data()


def get_balance(user_id):

    user_id = str(user_id)

    if user_id not in data:

        data[user_id] = 0
        save_data()

    return data[user_id]


def add_d(user_id, amount):

    user_id = str(user_id)

    data[user_id] = get_balance(user_id) + amount

    save_data()


def remove_d(user_id, amount):

    user_id = str(user_id)

    if get_balance(user_id) < amount:
        return False

    data[user_id] -= amount

    save_data()

    return True


# =========================
# Discord Bot
# =========================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():

    await bot.tree.sync()

    print(f"Bot 已登入：{bot.user}")
    print("D Coin Bot 已啟動")


# =========================
# 管理員紀錄
# =========================

async def send_log(message):

    channel = bot.get_channel(LOG_CHANNEL_ID)

    if channel is None:

        print("找不到 D 幣紀錄頻道")

        return

    try:

        await channel.send(message)

    except Exception as error:

        print(f"發送紀錄失敗：{error}")


# =========================
# /balance
# =========================

@bot.tree.command(
    name="balance",
    description="查看自己的 D 幣"
)
async def balance(
    interaction: discord.Interaction
):

    amount = get_balance(
        interaction.user.id
    )

    await interaction.response.send_message(

        f"💰 {interaction.user.mention}\n"
        f"你目前擁有 **{amount:,} D**"

    )


# =========================
# /addd
# =========================

@bot.tree.command(
    name="addd",
    description="管理員增加 D 幣"
)
@app_commands.describe(
    member="要增加 D 幣的成員",
    amount="增加的 D 幣數量"
)
async def addd(

    interaction: discord.Interaction,

    member: discord.Member,

    amount: int

):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(

            "❌ 只有管理員可以使用這個指令。",

            ephemeral=True

        )

        return


    if amount <= 0:

        await interaction.response.send_message(

            "❌ 數量必須大於 0。",

            ephemeral=True

        )

        return


    add_d(
        member.id,
        amount
    )


    new_balance = get_balance(
        member.id
    )


    await interaction.response.send_message(

        f"✅ 已給 {member.mention} **{amount:,} D**\n"
        f"💰 新餘額：**{new_balance:,} D**"

    )


    await send_log(

        f"💰 **D 幣增加紀錄**\n"
        f"👤 成員：{member.mention}\n"
        f"👮 操作者：{interaction.user.mention}\n"
        f"➕ 增加：**{amount:,} D**\n"
        f"💰 餘額：**{new_balance:,} D**"

    )


# =========================
# /removed
# =========================

@bot.tree.command(
    name="removed",
    description="管理員扣除 D 幣"
)
@app_commands.describe(
    member="要扣除 D 幣的成員",
    amount="扣除的 D 幣數量"
)
async def removed(

    interaction: discord.Interaction,

    member: discord.Member,

    amount: int

):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(

            "❌ 只有管理員可以使用這個指令。",

            ephemeral=True

        )

        return


    if amount <= 0:

        await interaction.response.send_message(

            "❌ 數量必須大於 0。",

            ephemeral=True

        )

        return


    if not remove_d(
        member.id,
        amount
    ):

        await interaction.response.send_message(

            f"❌ {member.mention} 的 D 幣不足。",

            ephemeral=True

        )

        return


    new_balance = get_balance(
        member.id
    )


    await interaction.response.send_message(

        f"✅ 已扣除 {member.mention} **{amount:,} D**\n"
        f"💰 新餘額：**{new_balance:,} D**"

    )


    await send_log(

        f"💸 **D 幣扣除紀錄**\n"
        f"👤 成員：{member.mention}\n"
        f"👮 操作者：{interaction.user.mention}\n"
        f"➖ 扣除：**{amount:,} D**\n"
        f"💰 餘額：**{new_balance:,} D**"

    )


# =========================
# /pay
# =========================

@bot.tree.command(
    name="pay",
    description="把 D 幣轉給其他成員"
)
@app_commands.describe(
    member="收款成員",
    amount="轉帳數量"
)
async def pay(

    interaction: discord.Interaction,

    member: discord.Member,

    amount: int

):

    if member.id == interaction.user.id:

        await interaction.response.send_message(

            "❌ 不能轉給自己。",

            ephemeral=True

        )

        return


    if member.bot:

        await interaction.response.send_message(

            "❌ 不能轉給 Bot。",

            ephemeral=True

        )

        return


    if amount <= 0:

        await interaction.response.send_message(

            "❌ 數量必須大於 0。",

            ephemeral=True

        )

        return


    if not remove_d(
        interaction.user.id,
        amount
    ):

        await interaction.response.send_message(

            "❌ 你的 D 幣不足。",

            ephemeral=True

        )

        return


    add_d(
        member.id,
        amount
    )


    sender_balance = get_balance(
        interaction.user.id
    )


    await interaction.response.send_message(

        f"✅ 已轉給 {member.mention} **{amount:,} D**\n"
        f"💰 你的餘額：**{sender_balance:,} D**"

    )


    await send_log(

        f"💸 **D 幣轉帳紀錄**\n"
        f"👤 付款：{interaction.user.mention}\n"
        f"👤 收款：{member.mention}\n"
        f"💰 金額：**{amount:,} D**\n"
        f"💰 付款方餘額：**{sender_balance:,} D**"

    )


# =========================
# /shop
# =========================

@bot.tree.command(
    name="shop",
    description="查看 D 幣商店"
)
async def shop(
    interaction: discord.Interaction
):

    message = (

        "🛒 **D 幣商店**\n\n"

        "🎁 **皮膚箱 ×1**\n"
        "💰 價格：**5,000 D**\n"
        "代碼：`skinbox`\n\n"

        "🏆 **限定稱號**\n"
        "💰 價格：**10,000 D**\n"
        "代碼：`title`\n\n"

        "💰 **有錢人身分組**\n"
        "💰 價格：**50,000 D**\n"
        "代碼：`rich`\n\n"

        "使用 `/buy` 兌換。"

    )


    await interaction.response.send_message(
        message
    )


# =========================
# /buy
# =========================

@bot.tree.command(
    name="buy",
    description="使用 D 幣兌換固定獎勵"
)
@app_commands.describe(
    item="商品代碼：skinbox / title / rich"
)
async def buy(

    interaction: discord.Interaction,

    item: str

):

    item = item.lower()


    if item not in SHOP_ITEMS:

        await interaction.response.send_message(

            "❌ 找不到這個商品。\n"
            "可使用：`skinbox`、`title`、`rich`",

            ephemeral=True

        )

        return


    product = SHOP_ITEMS[item]

    price = product["price"]

    product_name = product["name"]


    if not remove_d(
        interaction.user.id,
        price
    ):

        await interaction.response.send_message(

            f"❌ D 幣不足！\n"
            f"需要：**{price:,} D**\n"
            f"目前：**{get_balance(interaction.user.id):,} D**",

            ephemeral=True

        )

        return


    new_balance = get_balance(
        interaction.user.id
    )


    await interaction.response.send_message(

        f"✅ **兌換成功！**\n\n"
        f"🎁 獎勵：{product_name}\n"
        f"💰 花費：**{price:,} D**\n"
        f"💰 剩餘：**{new_balance:,} D**\n\n"
        f"📦 請等待管理員發放獎勵。"

    )


    await send_log(

        f"🛒 **D 幣兌換紀錄**\n"
        f"👤 成員：{interaction.user.mention}\n"
        f"🎁 商品：{product_name}\n"
        f"💰 花費：**{price:,} D**\n"
        f"💰 剩餘：**{new_balance:,} D**"

    )


# =========================
# 啟動
# =========================

if not TOKEN:

    raise RuntimeError(

        "找不到 DISCORD_TOKEN，"
        "請確認 Railway Variables 已設定。"

    )


bot.run(TOKEN)
