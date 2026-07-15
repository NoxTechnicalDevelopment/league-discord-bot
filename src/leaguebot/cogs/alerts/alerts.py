import random
from leaguebot.db import update_streak, get_streak, set_last_alert_streak

STREAK_THRESHOLD = 5

LOSS_MESSAGES = [
    "Maybe you should quit while you're ahead...",
    "Can't end on a loss, but maybe you should make an exception after {streak} losses...",
    "You're on a {streak}-game losing streak... maybe fuck off for the day 🤷",
    "After {streak} losses in a row, you might want to go touch some grass, or find a girlfriend or both",
    "You might need to change your underwear after this {streak} loss streak... it smells",
]

WIN_MESSAGES = [
    "{streak}-game win streak? Maybe time for a shower or food break. Maybe become a cigarette smoker like your grandfather.",
    "{streak} in a row? Whos letting you win?",
    "you must be Iron with {streak} wins in a row...",
    "Ain't no way you won {streak} in a row!",
    "Is that Faker? Only Faker could win {streak} in a row!",
    "Damn not even https://dpm.lol/NOTJT-6767 could win {streak} in a row",
]

async def process_result(discord_id: int, won: bool) -> str | None:
    # updates the streak and returns an alert message when the threshold is newly crossed
    # hits a multiple of streak threshold(5,10,15,20,...)
    current_streak, streak_type = await update_streak(discord_id, won)

    if current_streak < STREAK_THRESHOLD or current_streak % STREAK_THRESHOLD != 0:
        return None
    
    row = await get_streak(discord_id)
    last_alert = row["last_alert_streak"] if row else 0
    if current_streak == last_alert:
        return None
    
    await set_last_alert_streak(discord_id, current_streak)

    template = random.choice(LOSS_MESSAGES if streak_type == "loss" else WIN_MESSAGES)
    return template.format(streak=current_streak)

