import os
import json
import random
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands


TOKEN = os.getenv("DISCORD_TOKEN")

# ==========================================
# ID 設定
# ==========================================

LOG_CHANNEL_ID = 1538123620193280021

# ==========================================
# 軍銜身分組（能使用 /balance /daily /pay /shop /buy /lottery）
# ==========================================

RANK_ROLE_IDS = {
    "少尉": 1522176243561398392,
    "中尉": 1526456175673999500,
    "上尉": 1526456645150969956,
    "上校": 1529662506430107788,
    "最高統帥": 1522173016967217162,
}

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
# D 幣抽獎獎池（原本的抽獎券制改成 D 幣消耗）
# ==========================================

PRIZES = [
    ("💰 10 D", 60.0),
    ("💰 110 D", 30.0),
    ("💎 200 D", 9.0),
    ("🎁 皮膚箱 ×1", 0.9),
    ("👑 任意 1000 R 商品", 0.1)
]

LOTTERY_SINGLE_COST = 100
LOTTERY_TEN_COST = 950


# ==========================================
# 每日免費一抽
# ==========================================

DAILY_PRIZES = [
    ("💰 30 D", 5.0),
    ("💰 10 D", 15.0),
    ("💰 5 D", 10.0),
    ("😶 沒有獎勵", 70.0)
]


# ==========================================
# 釣魚模式設定
# ==========================================
# 重量（公斤，正整數）＝ 原始 D 幣價值
# 稀有度 ＝ 倍率
# 範例：50kg 史詩(x3) → 150 D

FISH_WEIGHT_TABLE = [
    (1, 10, 40.0),     # (最小重量, 最大重量, 機率%)
    (11, 30, 30.0),
    (31, 60, 18.0),
    (61, 100, 8.0),
    (101, 200, 3.5),
    (201, 400, 0.5)
]

RARITY_TABLE = [
    ("普通", 1, 55.0),
    ("稀有", 2, 30.0),
    ("史詩", 3, 12.0),
    ("傳說", 5, 2.7),
    ("神話", 10, 0.3)
]

FISHING_COST = 20  # 每次釣魚消耗的 D 幣


# ==========================================
# 賭硬幣設定
# ==========================================

COIN_MIN_BET = 100
COIN_MAX_BET = 10000


# ==========================================
# 骰子比大小設定
# ==========================================

DICE_MIN_BET = 100
DICE_MAX_BET = 10000


# ==========================================
# 拉霸機設定
# ==========================================

SLOTS_MIN_BET = 100
SLOTS_MAX_BET = 10000

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]

# 三個相同時的倍率
SLOT_PAYOUTS = {
    "🍒": 2,
    "🍋": 3,
    "🔔": 5,
    "⭐": 10,
    "💎": 20,
    "7️⃣": 50,
}

# 兩個相同時的倍率（固定）
SLOT_TWO_MATCH_PAYOUT = 1.5


# ==========================================
# 拆彈遊戲設定（5x5 地雷）
# ==========================================

MINES_MIN_BET = 100
MINES_MAX_BET = 10000

MINES_GRID_SIZE = 5
MINES_TOTAL_CELLS = MINES_GRID_SIZE * MINES_GRID_SIZE
MINES_MIN_BOMBS = 5

# 依炸彈數量對應「安全格獎勵倍率」（每翻開一格安全格增加的倍率）
# 炸彈越多，單格倍率越高
MINES_BOMB_MULTIPLIER = {
    5: 1.15,
    6: 1.20,
    7: 1.28,
    8: 1.35,
    9: 1.45,
    10: 1.55,
    12: 1.75,
    15: 2.10,
    18: 2.60,
    20: 3.20,
}


# ==========================================
# 資料庫
# ==========================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_data():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


data = load_data()


def ensure_user(user_id):

    user_id = str(user_id)

    if user_id not in data:

        data[user_id] = {
            "balance": 0,
            "tickets": 0,
            "last_daily": None
        }

        save_data()

    # 相容舊版只有數字的資料
    if isinstance(data[user_id], int):

        data[user_id] = {
            "balance": data[user_id],
            "tickets": 0,
            "last_daily": None
        }

        save_data()

    if "balance" not in data[user_id]:
        data[user_id]["balance"] = 0

    if "tickets" not in data[user_id]:
        data[user_id]["tickets"] = 0

    if "last_daily" not in data[user_id]:
        data[user_id]["last_daily"] = None

    return data[user_id]


# ==========================================
# D 幣
# ==========================================

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


# ==========================================
# 抽獎券（保留舊功能相容，daily 仍可能用到）
# ==========================================

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

    print(f"Bot 已登入：{bot.user}")

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Slash Commands 同步成功："
            f"{len(synced)} 個"
        )

        for command in synced:

            print(
                f"   /{command.name}"
            )

    except Exception as error:

        print(
            f"❌ Slash Commands 同步失敗："
            f"{error}"
        )

    print("D Coin Bot 已啟動")


# ==========================================
# 紀錄頻道
# ==========================================

def has_rank_permission(interaction: discord.Interaction) -> bool:

    # 最高統帥本身是管理員，一定可以使用
    if interaction.user.guild_permissions.administrator:

        return True

    user_role_ids = {
        role.id for role in interaction.user.roles
    }

    allowed_ids = set(
        RANK_ROLE_IDS.values()
    )

    return len(
        user_role_ids & allowed_ids
    ) > 0


async def send_log(message):

    try:

        channel = await bot.fetch_channel(
            LOG_CHANNEL_ID
        )

        await channel.send(message)

        print("✅ 紀錄已發送")

    except discord.Forbidden:

        print(
            "❌ Bot 沒有發送訊息權限"
        )

    except discord.NotFound:

        print(
            "❌ 找不到紀錄頻道"
        )

    except Exception as error:

        print(
            f"❌ 發送紀錄失敗：{error}"
        )


# ==========================================
# 一般抽獎（改為 D 幣消耗）
# ==========================================

def draw_prize():

    roll = random.uniform(
        0,
        100
    )

    current = 0

    for prize, chance in PRIZES:

        current += chance

        if roll <= current:

            return prize

    return PRIZES[-1][0]


def give_prize(user_id, prize):

    if prize == "💰 10 D":

        add_d(
            user_id,
            10
        )

    elif prize == "💰 110 D":

        add_d(
            user_id,
            110
        )

    elif prize == "💎 200 D":

        add_d(
            user_id,
            200
        )


# ==========================================
# 每日免費抽獎
# ==========================================

def draw_daily_prize():

    roll = random.uniform(
        0,
        100
    )

    current = 0

    for prize, chance in DAILY_PRIZES:

        current += chance

        if roll <= current:

            return prize

    return "😶 沒有獎勵"


def give_daily_prize(
    user_id,
    prize
):

    if prize == "💰 5 D":

        add_d(
            user_id,
            5
        )

    elif prize == "💰 10 D":

        add_d(
            user_id,
            10
        )

    elif prize == "💰 30 D":

        add_d(
            user_id,
            30
        )


# ==========================================
# 釣魚邏輯
# ==========================================

def roll_weight():

    roll = random.uniform(0, 100)
    current = 0

    for min_w, max_w, chance in FISH_WEIGHT_TABLE:

        current += chance

        if roll <= current:

            return random.randint(min_w, max_w)

    last_min, last_max, _ = FISH_WEIGHT_TABLE[-1]

    return random.randint(last_min, last_max)


def roll_rarity():

    roll = random.uniform(0, 100)
    current = 0

    for name, multiplier, chance in RARITY_TABLE:

        current += chance

        if roll <= current:

            return name, multiplier

    last_name, last_multiplier, _ = RARITY_TABLE[-1]

    return last_name, last_multiplier


def do_fishing():

    weight = roll_weight()
    rarity_name, multiplier = roll_rarity()

    reward = weight * multiplier

    return weight, rarity_name, multiplier, reward


# ==========================================
# /balance
# ==========================================

@bot.tree.command(
    name="balance",
    description="查看自己的 D 幣"
)
async def balance(
    interaction: discord.Interaction
):

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

    amount = get_balance(
        interaction.user.id
    )

    await interaction.response.send_message(
        f"💰 {interaction.user.mention}\n"
        f"你目前擁有 **{amount:,} D**"
    )


# ==========================================
# /daily
# ==========================================

@bot.tree.command(
    name="daily",
    description="每日免費領取 D 幣"
)
async def daily(
    interaction: discord.Interaction
):

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

    user_id = interaction.user.id

    user = ensure_user(
        user_id
    )

    now = datetime.now(
        timezone.utc
    )

    last_daily = user.get(
        "last_daily"
    )

    # ======================================
    # 檢查 24 小時
    # ======================================

    if last_daily:

        try:

            last_time = datetime.fromisoformat(
                last_daily
            )

            elapsed = (
                now - last_time
            )

            if elapsed < timedelta(
                hours=24
            ):

                remaining = (
                    timedelta(hours=24)
                    - elapsed
                )

                total_seconds = int(
                    remaining.total_seconds()
                )

                hours = (
                    total_seconds // 3600
                )

                minutes = (
                    total_seconds % 3600
                ) // 60

                await interaction.response.send_message(
                    f"⏰ **你今天已經領取過了！**\n\n"
                    f"下一次可以在 "
                    f"**{hours} 小時 "
                    f"{minutes} 分鐘**後領取。",
                    ephemeral=True
                )

                return

        except Exception:

            pass

    # ======================================
    # 記錄時間
    # ======================================

    user["last_daily"] = now.isoformat()

    save_data()

    # ======================================
    # 抽獎
    # ======================================

    prize = draw_daily_prize()

    give_daily_prize(
        user_id,
        prize
    )

    balance_amount = get_balance(
        user_id
    )

    # ======================================
    # 顯示結果
    # ======================================

    await interaction.response.send_message(
        f"🎁 **每日免費領取！**\n\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"🎉 抽到：**{prize}**\n\n"
        f"💰 D 幣：**{balance_amount:,} D**\n\n"
        f"⏰ **24 小時後可以再次領取！**"
    )

    # ======================================
    # 管理員紀錄
    # ======================================

    await send_log(
        f"🎁 **每日免費領取紀錄**\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"🆔 玩家 ID：`{user_id}`\n"
        f"🎉 結果：**{prize}**\n"
        f"💰 D 幣：**{balance_amount:,} D**"
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

    add_d(
        member.id,
        amount
    )

    new_balance = get_balance(
        member.id
    )

    await interaction.response.send_message(
        f"✅ 已給 {member.mention} "
        f"**{amount:,} D**\n"
        f"💰 新餘額："
        f"**{new_balance:,} D**"
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

    if not remove_d(
        member.id,
        amount
    ):

        await interaction.response.send_message(
            "❌ D 幣不足。",
            ephemeral=True
        )

        return

    new_balance = get_balance(
        member.id
    )

    await interaction.response.send_message(
        f"✅ 已扣除 {member.mention} "
        f"**{amount:,} D**\n"
        f"💰 新餘額："
        f"**{new_balance:,} D**"
    )

    await send_log(
        f"💸 **D 幣扣除紀錄**\n"
        f"👤 成員：{member.mention}\n"
        f"👮 操作者：{interaction.user.mention}\n"
        f"➖ 扣除：**{amount:,} D**\n"
        f"💰 餘額：**{new_balance:,} D**"
    )


# ==========================================
# 抽獎面板（改為 D 幣消耗制）
# ==========================================

class LotteryView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # ======================================
    # 單抽 100 D
    # ======================================

    @discord.ui.button(
        label=f"單抽 {LOTTERY_SINGLE_COST} D",
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

        if not remove_d(
            user_id,
            LOTTERY_SINGLE_COST
        ):

            await interaction.response.send_message(
                f"❌ D 幣不足！需要 **{LOTTERY_SINGLE_COST} D**\n"
                f"目前：**{get_balance(user_id):,} D**",
                ephemeral=True
            )

            return

        prize = draw_prize()

        give_prize(
            user_id,
            prize
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎰 **抽獎結果**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"💸 花費：**{LOTTERY_SINGLE_COST} D**\n"
            f"🎁 結果：**{prize}**\n\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎰 **單抽紀錄**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 花費：**{LOTTERY_SINGLE_COST} D**\n"
            f"🎁 結果：**{prize}**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

    # ======================================
    # 十連抽 950 D
    # ======================================

    @discord.ui.button(
        label=f"十連抽 {LOTTERY_TEN_COST} D",
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

        if not remove_d(
            user_id,
            LOTTERY_TEN_COST
        ):

            await interaction.response.send_message(
                f"❌ D 幣不足！需要 **{LOTTERY_TEN_COST} D**\n"
                f"目前：**{get_balance(user_id):,} D**",
                ephemeral=True
            )

            return

        results = []

        for _ in range(10):

            prize = draw_prize()

            results.append(
                prize
            )

            give_prize(
                user_id,
                prize
            )

        balance_amount = get_balance(
            user_id
        )

        message = (
            "🎰 **十連抽結果**\n\n"
        )

        for i, prize in enumerate(
            results,
            1
        ):

            message += (
                f"`{i}.` {prize}\n"
            )

        message += (
            f"\n👤 玩家：{interaction.user.mention}\n"
            f"💸 花費：**{LOTTERY_TEN_COST} D**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await interaction.response.send_message(
            message
        )

        log_message = (
            f"🎰 **十連抽紀錄**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 花費：**{LOTTERY_TEN_COST} D**\n"
            f"🎁 抽獎結果：\n"
        )

        for i, prize in enumerate(
            results,
            1
        ):

            log_message += (
                f"`{i}.` {prize}\n"
            )

        log_message += (
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            log_message
        )


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

    # ======================================
    # 檢查軍銜身分組
    # ======================================

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

    # ======================================
    # 抽獎面板
    # ======================================

    embed = discord.Embed(
        title="🎰 D 幣幸運抽獎",
        description=(
            f"🎟️ **單抽：{LOTTERY_SINGLE_COST} D**\n"
            f"🎰 **十連抽：{LOTTERY_TEN_COST} D**\n\n"

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
# /fish 釣魚
# ==========================================

@bot.tree.command(
    name="fish",
    description="釣魚！依重量和稀有度獲得 D 幣獎勵"
)
async def fish(
    interaction: discord.Interaction
):

    user_id = interaction.user.id

    if not remove_d(
        user_id,
        FISHING_COST
    ):

        await interaction.response.send_message(
            f"❌ D 幣不足！釣魚需要 **{FISHING_COST} D**\n"
            f"目前：**{get_balance(user_id):,} D**",
            ephemeral=True
        )

        return

    weight, rarity_name, multiplier, reward = do_fishing()

    add_d(
        user_id,
        reward
    )

    balance_amount = get_balance(
        user_id
    )

    await interaction.response.send_message(
        f"🎣 **釣魚結果！**\n\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"💸 花費：**{FISHING_COST} D**\n"
        f"🐟 重量：**{weight} kg**\n"
        f"✨ 稀有度：**{rarity_name} (x{multiplier})**\n"
        f"💰 獲得：**{reward:,} D**\n\n"
        f"💰 D 幣：**{balance_amount:,} D**"
    )

    await send_log(
        f"🎣 **釣魚紀錄**\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"🆔 玩家 ID：`{user_id}`\n"
        f"💸 花費：**{FISHING_COST} D**\n"
        f"🐟 重量：**{weight} kg**\n"
        f"✨ 稀有度：**{rarity_name} (x{multiplier})**\n"
        f"💰 獲得：**{reward:,} D**\n"
        f"💰 餘額：**{balance_amount:,} D**"
    )


# ==========================================
# /coinflip 賭硬幣
# ==========================================

@bot.tree.command(
    name="coinflip",
    description="賭硬幣：猜正面或反面，猜對兩倍，猜錯全沒"
)
@app_commands.describe(
    amount="下注金額（最少 100，最多 10000）",
    guess="猜正面還是反面"
)
@app_commands.choices(
    guess=[
        app_commands.Choice(name="正面", value="head"),
        app_commands.Choice(name="反面", value="tail"),
    ]
)
async def coinflip(
    interaction: discord.Interaction,
    amount: int,
    guess: app_commands.Choice[str]
):

    user_id = interaction.user.id

    # ======================================
    # 下注金額檢查
    # ======================================

    if amount < COIN_MIN_BET:

        await interaction.response.send_message(
            f"❌ 最少下注 **{COIN_MIN_BET} D**。",
            ephemeral=True
        )

        return

    if amount > COIN_MAX_BET:

        await interaction.response.send_message(
            f"❌ 最多下注 **{COIN_MAX_BET} D**。",
            ephemeral=True
        )

        return

    if not remove_d(
        user_id,
        amount
    ):

        await interaction.response.send_message(
            f"❌ D 幣不足！\n"
            f"目前：**{get_balance(user_id):,} D**",
            ephemeral=True
        )

        return

    # ======================================
    # 擲硬幣
    # ======================================

    result = random.choice(
        ["head", "tail"]
    )

    result_text = "🟡 正面" if result == "head" else "⚪ 反面"
    guess_text = "🟡 正面" if guess.value == "head" else "⚪ 反面"

    win = (result == guess.value)

    if win:

        payout = amount * 2

        add_d(
            user_id,
            payout
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🪙 **賭硬幣結果**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎯 你猜：{guess_text}\n"
            f"🎲 結果：{result_text}\n\n"
            f"🎉 **猜中了！贏得 {payout:,} D！**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🪙 **賭硬幣紀錄（贏）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🎯 猜測：{guess_text}\n"
            f"🎲 結果：{result_text}\n"
            f"💰 獲得：**{payout:,} D**\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    else:

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🪙 **賭硬幣結果**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎯 你猜：{guess_text}\n"
            f"🎲 結果：{result_text}\n\n"
            f"💔 **猜錯了！輸掉 {amount:,} D**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🪙 **賭硬幣紀錄（輸）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🎯 猜測：{guess_text}\n"
            f"🎲 結果：{result_text}\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )


# ==========================================
# /dice 骰子比大小
# ==========================================

@bot.tree.command(
    name="dice",
    description="骰子比大小：你 vs 莊家，各擲一顆骰子，點數大的贏"
)
@app_commands.describe(
    amount="下注金額（最少 100，最多 10000）"
)
async def dice(
    interaction: discord.Interaction,
    amount: int
):

    user_id = interaction.user.id

    if amount < DICE_MIN_BET:

        await interaction.response.send_message(
            f"❌ 最少下注 **{DICE_MIN_BET} D**。",
            ephemeral=True
        )

        return

    if amount > DICE_MAX_BET:

        await interaction.response.send_message(
            f"❌ 最多下注 **{DICE_MAX_BET} D**。",
            ephemeral=True
        )

        return

    if not remove_d(
        user_id,
        amount
    ):

        await interaction.response.send_message(
            f"❌ D 幣不足！\n"
            f"目前：**{get_balance(user_id):,} D**",
            ephemeral=True
        )

        return

    player_roll = random.randint(1, 6)
    dealer_roll = random.randint(1, 6)

    dice_emoji = {
        1: "⚀", 2: "⚁", 3: "⚂",
        4: "⚃", 5: "⚄", 6: "⚅"
    }

    player_text = f"{dice_emoji[player_roll]} ({player_roll})"
    dealer_text = f"{dice_emoji[dealer_roll]} ({dealer_roll})"

    # ======================================
    # 判定勝負
    # ======================================

    if player_roll > dealer_roll:

        payout = amount * 2

        add_d(
            user_id,
            payout
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎲 **骰子比大小**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🙋 你：{player_text}\n"
            f"🏦 莊家：{dealer_text}\n\n"
            f"🎉 **你贏了！獲得 {payout:,} D！**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎲 **骰子紀錄（贏）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🙋 玩家：{player_text} vs 🏦 莊家：{dealer_text}\n"
            f"💰 獲得：**{payout:,} D**\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    elif player_roll < dealer_roll:

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎲 **骰子比大小**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🙋 你：{player_text}\n"
            f"🏦 莊家：{dealer_text}\n\n"
            f"💔 **你輸了！輸掉 {amount:,} D**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎲 **骰子紀錄（輸）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🙋 玩家：{player_text} vs 🏦 莊家：{dealer_text}\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    else:

        # 平手，退回下注金額
        add_d(
            user_id,
            amount
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎲 **骰子比大小**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🙋 你：{player_text}\n"
            f"🏦 莊家：{dealer_text}\n\n"
            f"🤝 **平手！退回下注金額**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎲 **骰子紀錄（平手）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**（已退回）\n"
            f"🙋 玩家：{player_text} vs 🏦 莊家：{dealer_text}\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )


# ==========================================
# /slots 拉霸機
# ==========================================

@bot.tree.command(
    name="slots",
    description="拉霸機：轉出三個相同圖案獲得高倍獎勵"
)
@app_commands.describe(
    amount="下注金額（最少 100，最多 10000）"
)
async def slots(
    interaction: discord.Interaction,
    amount: int
):

    user_id = interaction.user.id

    if amount < SLOTS_MIN_BET:

        await interaction.response.send_message(
            f"❌ 最少下注 **{SLOTS_MIN_BET} D**。",
            ephemeral=True
        )

        return

    if amount > SLOTS_MAX_BET:

        await interaction.response.send_message(
            f"❌ 最多下注 **{SLOTS_MAX_BET} D**。",
            ephemeral=True
        )

        return

    if not remove_d(
        user_id,
        amount
    ):

        await interaction.response.send_message(
            f"❌ D 幣不足！\n"
            f"目前：**{get_balance(user_id):,} D**",
            ephemeral=True
        )

        return

    reels = [
        random.choice(SLOT_SYMBOLS)
        for _ in range(3)
    ]

    reels_text = " | ".join(reels)

    # ======================================
    # 判定結果
    # ======================================

    if reels[0] == reels[1] == reels[2]:

        multiplier = SLOT_PAYOUTS[reels[0]]

        payout = amount * multiplier

        add_d(
            user_id,
            payout
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎰 **拉霸機**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎡 {reels_text}\n\n"
            f"🎉 **三個相同！x{multiplier} 倍！獲得 {payout:,} D！**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎰 **拉霸機紀錄（大獎）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🎡 結果：{reels_text}\n"
            f"💰 獲得：**{payout:,} D**（x{multiplier}）\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    elif (
        reels[0] == reels[1]
        or reels[1] == reels[2]
        or reels[0] == reels[2]
    ):

        payout = int(amount * SLOT_TWO_MATCH_PAYOUT)

        add_d(
            user_id,
            payout
        )

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎰 **拉霸機**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎡 {reels_text}\n\n"
            f"✨ **兩個相同！小獎 {payout:,} D**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎰 **拉霸機紀錄（小獎）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🎡 結果：{reels_text}\n"
            f"💰 獲得：**{payout:,} D**\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    else:

        balance_amount = get_balance(
            user_id
        )

        await interaction.response.send_message(
            f"🎰 **拉霸機**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🎡 {reels_text}\n\n"
            f"💔 **沒中獎！輸掉 {amount:,} D**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        await send_log(
            f"🎰 **拉霸機紀錄（未中獎）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{user_id}`\n"
            f"💸 下注：**{amount:,} D**\n"
            f"🎡 結果：{reels_text}\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )


# ==========================================
# 拆彈遊戲（5x5 地雷）
# ==========================================

def get_bomb_multiplier(bomb_count: int) -> float:

    # 找出小於等於 bomb_count 的最大設定值
    keys = sorted(MINES_BOMB_MULTIPLIER.keys())

    chosen = keys[0]

    for k in keys:

        if bomb_count >= k:

            chosen = k

        else:

            break

    return MINES_BOMB_MULTIPLIER[chosen]


class MinesView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        amount: int,
        bomb_count: int
    ):

        super().__init__(timeout=120)

        self.owner_id = owner_id
        self.amount = amount
        self.bomb_count = bomb_count
        self.per_cell_multiplier = get_bomb_multiplier(bomb_count)

        self.opened = 0
        self.current_multiplier = 1.0
        self.game_over = False

        # 隨機排列地雷位置
        positions = list(range(MINES_TOTAL_CELLS))
        random.shuffle(positions)

        self.bomb_positions = set(positions[:bomb_count])

        # 建立 25 個按鈕
        for i in range(MINES_TOTAL_CELLS):

            button = discord.ui.Button(
                label="❔",
                style=discord.ButtonStyle.secondary,
                row=i // MINES_GRID_SIZE,
                custom_id=f"mine_{i}"
            )

            button.callback = self.make_callback(i)

            self.add_item(button)

        # 兌現按鈕
        self.cashout_button = discord.ui.Button(
            label="💰 兌現",
            style=discord.ButtonStyle.success,
            row=MINES_GRID_SIZE,
            custom_id="mine_cashout"
        )

        self.cashout_button.callback = self.cashout_callback

        self.add_item(self.cashout_button)

    def make_callback(self, index: int):

        async def callback(interaction: discord.Interaction):

            await self.handle_click(interaction, index)

        return callback

    async def handle_click(
        self,
        interaction: discord.Interaction,
        index: int
    ):

        if interaction.user.id != self.owner_id:

            await interaction.response.send_message(
                "❌ 這不是你的遊戲。",
                ephemeral=True
            )

            return

        if self.game_over:

            await interaction.response.send_message(
                "❌ 這局遊戲已經結束了。",
                ephemeral=True
            )

            return

        clicked_button = None

        for item in self.children:

            if getattr(item, "custom_id", None) == f"mine_{index}":

                clicked_button = item

                break

        if clicked_button is None or clicked_button.disabled:

            await interaction.response.send_message(
                "❌ 這格已經翻開了。",
                ephemeral=True
            )

            return

        # ======================================
        # 踩到炸彈
        # ======================================

        if index in self.bomb_positions:

            self.game_over = True

            self.reveal_all(exploded_index=index)

            for item in self.children:

                item.disabled = True

            await interaction.response.edit_message(
                content=(
                    f"💣 **踩到炸彈了！**\n\n"
                    f"👤 玩家：{interaction.user.mention}\n"
                    f"🧨 炸彈數量：**{self.bomb_count} 顆**\n"
                    f"💸 下注：**{self.amount:,} D**\n\n"
                    f"💔 **全部輸掉了！**"
                ),
                view=self
            )

            await send_log(
                f"💣 **拆彈紀錄（爆炸）**\n"
                f"👤 玩家：{interaction.user.mention}\n"
                f"🆔 玩家 ID：`{self.owner_id}`\n"
                f"🧨 炸彈數量：**{self.bomb_count} 顆**\n"
                f"💸 下注：**{self.amount:,} D**\n"
                f"🔓 已開啟安全格：**{self.opened} 格**\n"
                f"💰 損失：**{self.amount:,} D**"
            )

            return

        # ======================================
        # 安全格
        # ======================================

        self.opened += 1

        self.current_multiplier *= self.per_cell_multiplier

        clicked_button.label = "💎"
        clicked_button.style = discord.ButtonStyle.success
        clicked_button.disabled = True

        potential_payout = int(
            self.amount * self.current_multiplier
        )

        safe_cells_left = MINES_TOTAL_CELLS - self.bomb_count - self.opened

        await interaction.response.edit_message(
            content=(
                f"💎 **拆彈進行中**\n\n"
                f"👤 玩家：{interaction.user.mention}\n"
                f"🧨 炸彈數量：**{self.bomb_count} 顆**\n"
                f"💸 下注：**{self.amount:,} D**\n"
                f"🔓 已開啟：**{self.opened} 格**（剩餘安全格：{safe_cells_left}）\n"
                f"📈 目前倍率：**x{self.current_multiplier:.2f}**\n"
                f"💰 目前可兌現：**{potential_payout:,} D**\n\n"
                f"⚠️ 隨時可以按「💰 兌現」停止，或繼續冒險翻更多格！"
            ),
            view=self
        )

        # 全部安全格都翻完了，自動兌現
        if safe_cells_left <= 0:

            await self.finish_cashout(interaction, auto=True)

    async def cashout_callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.owner_id:

            await interaction.response.send_message(
                "❌ 這不是你的遊戲。",
                ephemeral=True
            )

            return

        if self.game_over:

            await interaction.response.send_message(
                "❌ 這局遊戲已經結束了。",
                ephemeral=True
            )

            return

        if self.opened == 0:

            await interaction.response.send_message(
                "❌ 你還沒翻開任何一格，無法兌現。",
                ephemeral=True
            )

            return

        await self.finish_cashout(interaction, auto=False)

    async def finish_cashout(
        self,
        interaction: discord.Interaction,
        auto: bool
    ):

        self.game_over = True

        payout = int(self.amount * self.current_multiplier)

        add_d(
            self.owner_id,
            payout
        )

        balance_amount = get_balance(
            self.owner_id
        )

        self.reveal_all(exploded_index=None)

        for item in self.children:

            item.disabled = True

        content = (
            f"💰 **{'全部翻完，自動兌現！' if auto else '成功兌現！'}**\n\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🧨 炸彈數量：**{self.bomb_count} 顆**\n"
            f"💸 下注：**{self.amount:,} D**\n"
            f"🔓 開啟安全格：**{self.opened} 格**\n"
            f"📈 最終倍率：**x{self.current_multiplier:.2f}**\n"
            f"🎉 **獲得：{payout:,} D！**\n"
            f"💰 D 幣：**{balance_amount:,} D**"
        )

        if auto:

            await interaction.followup.send(
                content,
                view=self
            )

        else:

            await interaction.response.edit_message(
                content=content,
                view=self
            )

        await send_log(
            f"💰 **拆彈紀錄（兌現）**\n"
            f"👤 玩家：{interaction.user.mention}\n"
            f"🆔 玩家 ID：`{self.owner_id}`\n"
            f"🧨 炸彈數量：**{self.bomb_count} 顆**\n"
            f"💸 下注：**{self.amount:,} D**\n"
            f"🔓 開啟安全格：**{self.opened} 格**\n"
            f"📈 最終倍率：**x{self.current_multiplier:.2f}**\n"
            f"💰 獲得：**{payout:,} D**\n"
            f"💰 餘額：**{balance_amount:,} D**"
        )

    def reveal_all(self, exploded_index):

        for item in self.children:

            custom_id = getattr(item, "custom_id", "")

            if not custom_id.startswith("mine_") or custom_id == "mine_cashout":

                continue

            index = int(custom_id.split("_")[1])

            if item.disabled:

                continue

            if index in self.bomb_positions:

                if index == exploded_index:

                    item.label = "💥"
                    item.style = discord.ButtonStyle.danger

                else:

                    item.label = "💣"
                    item.style = discord.ButtonStyle.secondary

                item.disabled = True

            else:

                item.label = "▫️"
                item.disabled = True

    async def on_timeout(self):

        if not self.game_over and self.opened > 0:

            # 逾時自動退回原始下注金額（不含獲利），避免卡住玩家資金
            add_d(self.owner_id, self.amount)

        self.game_over = True

        for item in self.children:

            item.disabled = True


# ==========================================
# /mines 拆彈遊戲
# ==========================================

@bot.tree.command(
    name="mines",
    description="拆彈遊戲：5x5 地雷，越多炸彈倍率越高，全靠運氣"
)
@app_commands.describe(
    amount="下注金額（最少 100，最多 10000）",
    bombs="炸彈數量（最少 5 顆，最多 20 顆）"
)
async def mines(
    interaction: discord.Interaction,
    amount: int,
    bombs: int
):

    user_id = interaction.user.id

    if amount < MINES_MIN_BET:

        await interaction.response.send_message(
            f"❌ 最少下注 **{MINES_MIN_BET} D**。",
            ephemeral=True
        )

        return

    if amount > MINES_MAX_BET:

        await interaction.response.send_message(
            f"❌ 最多下注 **{MINES_MAX_BET} D**。",
            ephemeral=True
        )

        return

    if bombs < MINES_MIN_BOMBS:

        await interaction.response.send_message(
            f"❌ 炸彈數量最少要 **{MINES_MIN_BOMBS} 顆**。",
            ephemeral=True
        )

        return

    if bombs >= MINES_TOTAL_CELLS:

        await interaction.response.send_message(
            f"❌ 炸彈數量最多 **{MINES_TOTAL_CELLS - 1} 顆**（要留至少 1 格安全格）。",
            ephemeral=True
        )

        return

    if not remove_d(
        user_id,
        amount
    ):

        await interaction.response.send_message(
            f"❌ D 幣不足！\n"
            f"目前：**{get_balance(user_id):,} D**",
            ephemeral=True
        )

        return

    view = MinesView(
        owner_id=user_id,
        amount=amount,
        bomb_count=bombs
    )

    await interaction.response.send_message(
        f"💣 **拆彈遊戲開始！**\n\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"🧨 炸彈數量：**{bombs} 顆**（共 {MINES_TOTAL_CELLS} 格）\n"
        f"💸 下注：**{amount:,} D**\n"
        f"📈 每格倍率：**x{view.per_cell_multiplier}**\n\n"
        f"點擊格子翻開，沒有任何提示，全憑運氣！\n"
        f"隨時可以按「💰 兌現」把目前獎勵收下。",
        view=view
    )

    await send_log(
        f"💣 **拆彈遊戲開始**\n"
        f"👤 玩家：{interaction.user.mention}\n"
        f"🆔 玩家 ID：`{user_id}`\n"
        f"🧨 炸彈數量：**{bombs} 顆**\n"
        f"💸 下注：**{amount:,} D**"
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

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

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

    remaining = get_balance(
        interaction.user.id
    )

    await interaction.response.send_message(
        f"✅ 已轉給 {member.mention} "
        f"**{amount:,} D**\n"
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

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

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

    await interaction.response.send_message(
        message
    )


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

    if not has_rank_permission(interaction):

        await interaction.response.send_message(
            "❌ 你沒有軍銜，無法使用此指令。",
            ephemeral=True
        )

        return

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
