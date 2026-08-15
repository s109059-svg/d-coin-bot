import os
import json
import random
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

LOG_CHANNEL_ID = 1538123620193280021
DATA_FILE = "data.json"

# ==========================================
# 商店
# ==========================================

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

# ==========================================
# 抽獎獎池
# ==========================================

PRIZES = [
    ("💰 10 D", 60.0),
    ("💰 110 D", 30.0),
    ("💎 200 D", 9.0),
    ("🎁 皮膚箱 ×1", 0.9),
    ("👑 任意 1000 R 商品", 0.1)
]

# ==========================================
# 資料庫
# ==========================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


data = load_data()


def ensure_user(user_id):
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "balance": 0,
            "tickets": 0
        }
        save_data()

    # 相容舊版只有數字的資料
    if isinstance(data[user_id], int):
        data[user_id] = {
            "balance": data[user_id],
            "tickets": 0
        }
        save_data()

    if "balance" not in data[user_id]:
        data[user_id]["balance"] = 0

    if "tickets" not in data[user_id]:
        data[user_id]["tickets"] = 0

    return data[user_id]


def get_balance(user_id):
    return ensure_user(user_id)["balance"]


def add_d(user_id, amount):
    user = ensure_user(user_id)
    user["balance"] += amount
    save_data()


def remove_d(user_id, amount):
    user = ensure_user(user_id)

    if user["balance"] < amount:
        return False

    user["balance"] -= amount
    save_data()
    return True


def get_tickets(user_id):
    return ensure_user(user_id)["tickets"]


def add_tickets(user_id, amount):
    user = ensure_user(user_id)
    user["tickets"] += amount
    save_data()


def remove_tickets(user_id, amount):
    user = ensure_user(user_id)

    if user["tickets"] < amount:
        return False

    user["tickets"] -= amount
    save_data()
    return True


# ==========================================
# Bot
# ==========================================

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


# ==========================================
# 紀錄頻道
# ==========================================

async def send_log(message):
    try:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)

        await channel.send(message)

        print("✅ 抽獎紀錄已發送")

    except discord.Forbidden:
        print("❌ Bot 沒有發送訊息權限")

    except discord.NotFound:
        print("❌ 找不到紀錄頻道")

    except Exception as error:
        print(f"❌ 發送紀錄失敗：{error}")


# ==========================================
# 抽獎
# ==========================================

def draw_prize():
    roll = random.uniform(0, 100)
    current = 0

    for prize, chance in PRIZES:
        current += chance

        if roll <= current:
            return prize

    return PRIZES[-1][0]


def give_prize(user_id, prize):
    if prize == "💰 10 D":
        add_d(user_id, 10)

    elif prize == "💰 110 D":
        add_d(user_id, 110)

    elif prize == "💎 200 D":
        add_d(user_id, 200)


# ==========================================
# /balance
# ==========================================

@bot.tree.command(
    name="balance",
    description="查看自己的 D 幣"
)
async def balance(interaction: discord.Interaction):

    amount = get_balance(interaction.user.id)

    await interaction.response.send_message(
        f"💰 {interaction.user.mention}\n"
        f"你目前擁有 **{amount:,} D**"
    )


# ==========================================
# /tickets
# ==========================================

@bot.tree.command(
    name="tickets",
    description="查看自己的抽獎券"
)
async def tickets(interaction: discord.Interaction):

    amount = get_tickets(interaction.user.id)

    await interaction.response.send_message(
        f"🎟️ {interaction.user.mention}\n"
        f"你目前擁有 **{amount} 張抽獎券**"
    )


# ==========================================
# /addd
# ==========================================

@bot.tree.command(
    name="addd",
    description="管理員增加 D 幣"
)
@app_commands.describe(
    member="成員",
    amount="D 幣數量"
)
async def addd(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ 只有管理員可以使用。",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ 數量必須大於 0。",
            ephemeral=True
        )
        return

    add_d(member.id, amount)

    new_balance = get_balance(member.id)

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


# ==========================================
# /removed
# ==========================================

@bot.tree.command(
    name="removed",
    description="管理員扣除 D 幣"
)
@app_commands.describe(
    member="成員",
    amount="D 幣數量"
)
async def removed(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ 只有管理員可以使用。",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ 數量必須大於 0。",
            ephemeral=True
        )
        return

    if not remove_d(member.id, amount):
        await interaction.response.send_message(
            "❌ D 幣不足。",
            ephemeral=True
        )
        return

    new_balance = get_balance(member.id)

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


# ==========================================
# /addticket
# ==========================================

@bot.tree.command(
    name="addticket",
    description="管理員發放抽獎券"
)
@app_commands.describe(
    member="成員",
    amount="抽獎券數量"
)
async def addticket(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ 只有管理員可以使用。",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ 數量必須大於 0。",
            ephemeral=True
        )
        return

    add_tickets(member.id, amount)

    new_amount = get_tickets(member.id)

    await interaction.response.send_message(
        f"🎟️ 已給 {member.mention} **{amount} 張抽獎券**\n"
        f"🎟️ 目前：**{new_amount} 張**"
    )

    await send_log(
        f"🎟️ **抽獎券發放紀錄**\n"
        f"👤 成員：{member.mention}\n"
        f"👮 操作者：{interaction.user.mention}\n"
        f"➕ 發放：**{amount} 張**\n"
        f"🎟️ 剩餘：**{new_amount} 張**"
    )


# ==========================================
# 抽獎面板
# ==========================================

class LotteryView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # --------------------------------------
    # 單抽
    # --------------------------------------

    @discord.ui.button(
        label="單抽",
        emoji="🎟️",
        style=discord.ButtonStyle.primary,
        custom_id="lottery_single"
    )
    async def single(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = interaction.user.id

        if get_tickets(user_id) < 1:

            await interaction.response.send_message(
                "❌ 你沒有抽獎券！",
                ephemeral=True
            )

            return

        remove_tickets(user_id, 1)

        prize = draw_prize()

        give_prize(user_id, prize)

        remaining = get_tickets(user_id)

        balance = get_balance(user_id)

        await interaction.response.send_message(
            f"🎰 **抽獎結果**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎁 結果：**{prize}**\n\n"
            f"🎟️ 剩餘抽獎券：**{remaining}**\n"
            f"💰 D 幣：**{balance:,} D**"
        )

        await send_log(
            f"🎰 **單抽紀錄**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"🎁 結果：**{prize}**\n"
            f"🎟️ 剩餘抽獎券：**{remaining}**\n"
            f"💰 D 幣：**{balance:,} D**"
        )

    # --------------------------------------
    # 十連抽
    # --------------------------------------

    @discord.ui.button(
        label="十連抽",
        emoji="🎰",
        style=discord.ButtonStyle.success,
        custom_id="lottery_ten"
    )
    async def ten(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = interaction.user.id

        if get_tickets(user_id) < 10:

            await interaction.response.send_message(
                "❌ 你需要至少 **10 張抽獎券**！",
                ephemeral=True
            )

            return

        remove_tickets(user_id, 10)

        results = []

        for _ in range(10):

            prize = draw_prize()

            results.append(prize)

            give_prize(user_id, prize)

        remaining = get_tickets(user_id)

        balance = get_balance(user_id)

        message = "🎰 **十連抽結果**\n\n"

        for i, prize in enumerate(results, 1):

            message += f"`{i}.` {prize}\n"

        message += (
            f"\n👤 玩家：{interaction.user.mention}\n"
            f"🎟️ 剩餘抽獎券：**{remaining}**\n"
            f"💰 D 幣：**{balance:,} D**"
        )

        await interaction.response.send_message(message)

        log_message = (
            f"🎰 **十連抽紀錄**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"🎟️ 消耗：**10 張抽獎券**\n"
            f"🎁 抽獎結果：\n"
        )

        for i, prize in enumerate(results, 1):

            log_message += f"`{i}.` {prize}\n"

        log_message += (
            f"🎟️ 剩餘抽獎券：**{remaining}**\n"
            f"💰 D 幣：**{balance:,} D**"
        )

        await send_log(log_message)


# ==========================================
# /lottery
# ==========================================

@bot.tree.command(
    name="lottery",
    description="建立抽獎面板"
)
async def lottery(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ 只有管理員可以建立抽獎面板。",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🎰 D 幣幸運抽獎",
        description=(
            "🎟️ 使用抽獎券參加\n\n"

            "🎟️ **單抽：1 張**\n"
            "🎰 **十連抽：10 張**\n\n"

            "💰 10 D — **60%**\n"
            "💰 110 D — **30%**\n"
            "💎 200 D — **9%**\n"
            "🎁 皮膚箱 ×1 — **0.9%**\n"
            "👑 任意 1000 R 商品 — **0.1%**"
        )
    )

    embed.set_footer(
        text="每次抽獎都有獎勵！"
    )

    await interaction.response.send_message(
        embed=embed,
        view=LotteryView()
    )


# ==========================================
# /pay
# ==========================================

@bot.tree.command(
    name="pay",
    description="轉移 D 幣"
)
@app_commands.describe(
    member="收款成員",
    amount="D 幣數量"
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

    add_d(member.id, amount)

    remaining = get_balance(
        interaction.user.id
    )

    await interaction.response.send_message(
        f"✅ 已轉給 {member.mention} **{amount:,} D**\n"
        f"💰 剩餘：**{remaining:,} D**"
    )

    await send_log(
        f"💸 **D 幣轉帳紀錄**\n"
        f"👤 付款：{interaction.user.mention}\n"
        f"👤 收款：{member.mention}\n"
        f"💰 金額：**{amount:,} D**"
    )


# ==========================================
# /shop
# ==========================================

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
        "💰 5,000 D\n"
        "代碼：`skinbox`\n\n"

        "🏆 **限定稱號**\n"
        "💰 10,000 D\n"
        "代碼：`title`\n\n"

        "💰 **有錢人身分組**\n"
        "💰 50,000 D\n"
        "代碼：`rich`\n\n"

        "使用 `/buy` 兌換。"
    )

    await interaction.response.send_message(message)


# ==========================================
# /buy
# ==========================================

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
            "❌ 找不到商品。\n"
            "可用：`skinbox`、`title`、`rich`",
            ephemeral=True
        )

        return

    product = SHOP_ITEMS[item]

    price = product["price"]
    name = product["name"]

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

    remaining = get_balance(
        interaction.user.id
    )

    await interaction.response.send_message(
        f"✅ **兌換成功！**\n\n"
        f"🎁 {name}\n"
        f"💰 花費：**{price:,} D**\n"
        f"💰 剩餘：**{remaining:,} D**\n\n"
        f"📦 請等待管理員發放。"
    )

    await send_log(
        f"🛒 **商店兌換紀錄**\n"
        f"👤 成員：{interaction.user.mention}\n"
        f"🎁 商品：{name}\n"
        f"💰 花費：**{price:,} D**\n"
        f"💰 剩餘：**{remaining:,} D**"
    )


# ==========================================
# 啟動
# ==========================================

if not TOKEN:
    raise RuntimeError(
        "找不到 DISCORD_TOKEN，請確認 Railway Variables。"
    )

bot.run(TOKEN)
