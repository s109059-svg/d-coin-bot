import os
import random
import json
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "data.json"

# =========================
# 抽獎設定
# =========================

SINGLE_COST = 100
TEN_COST = 950

PRIZES = [
    ("❌ 沒抽中", 40),
    ("💰 110 D", 30),
    ("💎 200 D", 20),
    ("🎁 皮膚箱 ×1", 9),
    ("👑 超大獎：任意 1000 R 商品", 1),
]

# =========================
# 資料庫
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


data = load_data()


def get_balance(user_id):
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = 0
        save_data(data)

    return data[user_id]


def add_d(user_id, amount):
    user_id = str(user_id)
    data[user_id] = get_balance(user_id) + amount
    save_data(data)


def remove_d(user_id, amount):
    user_id = str(user_id)
    data[user_id] = get_balance(user_id) - amount
    save_data(data)


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


# =========================
# /balance
# =========================

@bot.tree.command(name="balance", description="查看你的 D 幣")
async def balance(interaction: discord.Interaction):

    amount = get_balance(interaction.user.id)

    await interaction.response.send_message(
        f"💰 {interaction.user.mention} 目前擁有 **{amount} D**"
    )


# =========================
# /addd
# =========================

@bot.tree.command(name="addd", description="增加 D 幣（管理員）")
@app_commands.describe(
    member="要增加 D 幣的成員",
    amount="增加多少 D 幣"
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

    add_d(member.id, amount)

    await interaction.response.send_message(
        f"✅ 已給 {member.mention} **{amount} D**\n"
        f"💰 目前餘額：**{get_balance(member.id)} D**"
    )


# =========================
# 抽獎
# =========================

def draw_prize():

    roll = random.uniform(0, 100)
    current = 0

    for prize, chance in PRIZES:
        current += chance

        if roll <= current:
            return prize

    return "❌ 沒抽中"


async def do_draw(user, times):

    cost = SINGLE_COST if times == 1 else TEN_COST
    balance = get_balance(user.id)

    if balance < cost:
        return (
            False,
            f"❌ 你的 D 幣不足！\n"
            f"需要：**{cost} D**\n"
            f"目前：**{balance} D**"
        )

    remove_d(user.id, cost)

    results = []

    for _ in range(times):

        prize = draw_prize()
        results.append(prize)

        # D 幣獎勵
        if prize == "💰 110 D":
            add_d(user.id, 110)

        elif prize == "💎 200 D":
            add_d(user.id, 200)

    return True, results


# =========================
# 抽獎面板
# =========================

class LotteryView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="單抽 100 D",
        style=discord.ButtonStyle.primary,
        emoji="🎟️",
        custom_id="lottery_single"
    )
    async def single_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        success, result = await do_draw(
            interaction.user,
            1
        )

        if not success:
            await interaction.response.send_message(
                result,
                ephemeral=True
            )
            return

        prize = result[0]

        message = (
            f"🎰 **抽獎結果**\n\n"
            f"{prize}\n\n"
            f"💰 剩餘 D 幣："
            f"**{get_balance(interaction.user.id)} D**"
        )

        if "超大獎" in prize:
            message += (
                "\n\n🚨 **恭喜！你抽中了超大獎！**\n"
                "請等待管理員聯絡你領取獎勵。"
            )

        elif "皮膚箱" in prize:
            message += "\n\n🎁 請聯絡管理員領取皮膚箱。"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


    @discord.ui.button(
        label="十連抽 950 D",
        style=discord.ButtonStyle.success,
        emoji="🎰",
        custom_id="lottery_ten"
    )
    async def ten_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        success, result = await do_draw(
            interaction.user,
            10
        )

        if not success:
            await interaction.response.send_message(
                result,
                ephemeral=True
            )
            return

        message = "🎰 **十連抽結果**\n\n"

        for i, prize in enumerate(result, 1):
            message += f"`{i}.` {prize}\n"

        message += (
            f"\n💰 剩餘 D 幣："
            f"**{get_balance(interaction.user.id)} D**"
        )

        if any("超大獎" in prize for prize in result):
            message += (
                "\n\n🚨 **有人抽中超大獎！**\n"
                "請管理員處理獎勵。"
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# =========================
# /lottery
# =========================

@bot.tree.command(
    name="lottery",
    description="建立 D 幣抽獎面板"
)
async def lottery(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ 只有管理員可以建立抽獎面板。",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎰 D 幣幸運抽獎",
        description=(
            "使用 D 幣進行抽獎！\n\n"
            "🎟️ **單抽：100 D**\n"
            "🎰 **十連抽：950 D**\n\n"
            "❌ 沒抽中｜40%\n"
            "💰 110 D｜30%\n"
            "💎 200 D｜20%\n"
            "🎁 皮膚箱 ×1｜9%\n"
            "👑 任意 1000 R 商品｜1%"
        ),
    )

    embed.set_footer(
        text="祝你好運！🎰"
    )

    await interaction.response.send_message(
        embed=embed,
        view=LotteryView()
    )


# =========================
# 啟動
# =========================

if not TOKEN:
    raise RuntimeError(
        "找不到 DISCORD_TOKEN，請在 Railway 設定環境變數。"
    )

bot.run(TOKEN)
