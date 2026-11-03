"""Telegram bot: send a @username, get that user's active stories back.

Bots cannot read stories through the Bot API, so a second client logged in
as a regular user account (userbot) fetches them. Stories are fetched with
stories.getPeerStories and downloaded directly; stories.readStories /
incrementStoryViews are never called, so no view is registered.
"""

import os
import re
import time
import asyncio
import tempfile
import logging

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import (
    UsernameInvalidError,
    UsernameNotOccupiedError,
    FloodWaitError,
    PhoneNumberInvalidError,
)
from telethon.tl.functions.stories import GetPeerStoriesRequest, GetPinnedStoriesRequest
from telethon.tl.types import StoryItem, MessageMediaPhoto

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
# Comma-separated Telegram user IDs allowed to use the bot (empty = everyone)
ALLOWED_IDS = {int(x) for x in os.getenv("ALLOWED_IDS", "").split(",") if x.strip()}
# Minimum seconds between two requests from the same user
COOLDOWN = int(os.getenv("COOLDOWN", "10"))
SESSION_DIR = os.getenv("SESSION_DIR", ".")

ALBUM_SIZE = 10  # Telegram limit for one media group
USERNAME_RE = re.compile(r"^(?:https?://t\.me/|@)?([A-Za-z0-9_]{4,32})$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("story-bot")

os.makedirs(SESSION_DIR, exist_ok=True)
user = TelegramClient(os.path.join(SESSION_DIR, "user_session"), API_ID, API_HASH)
bot = TelegramClient(os.path.join(SESSION_DIR, "bot_session"), API_ID, API_HASH)

# One userbot request at a time keeps the account well below flood limits
user_lock = asyncio.Lock()
last_request: dict[int, float] = {}


async def fetch_stories(username: str, pinned: bool) -> list[StoryItem]:
    peer = await user.get_input_entity(username)
    if pinned:
        res = await user(GetPinnedStoriesRequest(peer=peer, offset_id=0, limit=50))
        items = res.stories
    else:
        res = await user(GetPeerStoriesRequest(peer=peer))
        items = res.stories.stories
    # Skipped/deleted placeholders carry no media
    return [s for s in items if isinstance(s, StoryItem) and s.media]


def story_caption(username: str, s: StoryItem) -> str:
    caption = f"@{username} · {s.date:%Y-%m-%d %H:%M} UTC"
    if s.caption:
        caption += f"\n\n{s.caption}"
    return caption[:1024]


async def send_stories(event, username: str, pinned: bool):
    status = await event.reply(f"⏳ @{username} storylari olinmoqda...")
    try:
        async with user_lock:
            stories = await fetch_stories(username, pinned)
    except (UsernameInvalidError, UsernameNotOccupiedError, ValueError):
        await status.edit("❌ Bunday username topilmadi.")
        return
    except FloodWaitError as e:
        await status.edit(f"⏱ Telegram limit qo'ydi, {e.seconds} soniyadan keyin urinib ko'ring.")
        return

    if not stories:
        kind = "pin qilingan" if pinned else "aktiv"
        await status.edit(f"ℹ️ @{username} da {kind} story yo'q (yoki faqat yaqinlarga ochiq).")
        return

    await status.edit(f"📥 {len(stories)} ta story topildi, yuborilmoqda...")
    with tempfile.TemporaryDirectory() as tmp:
        # Send as albums of up to 10 instead of one message per story
        for i in range(0, len(stories), ALBUM_SIZE):
            paths, captions = [], []
            async with user_lock:
                for s in stories[i:i + ALBUM_SIZE]:
                    ext = ".jpg" if isinstance(s.media, MessageMediaPhoto) else ".mp4"
                    path = await user.download_media(
                        s.media, file=os.path.join(tmp, f"{s.id}{ext}")
                    )
                    if path:
                        paths.append(path)
                        captions.append(story_caption(username, s))
            if len(paths) == 1:
                await bot.send_file(
                    event.chat_id, paths[0], caption=captions[0], supports_streaming=True
                )
            elif paths:
                await bot.send_file(
                    event.chat_id, paths, caption=captions, supports_streaming=True
                )
    await status.delete()


@bot.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return
    if ALLOWED_IDS and event.sender_id not in ALLOWED_IDS:
        await event.reply("⛔ Sizga ruxsat yo'q.")
        return

    text = (event.raw_text or "").strip()
    if text in ("/start", "/help"):
        await event.reply(
            "Username yuboring: `@username` yoki `t.me/username` — aktiv storylarni olib beraman.\n"
            "`/pinned @username` — profilga pin qilingan storylar.",
            parse_mode="md",
        )
        return

    pinned = False
    if text.startswith("/pinned"):
        pinned = True
        text = text[len("/pinned"):].strip()

    m = USERNAME_RE.match(text)
    if not m:
        await event.reply("Username noto'g'ri. Masalan: `@durov`", parse_mode="md")
        return

    now = time.monotonic()
    wait = COOLDOWN - (now - last_request.get(event.sender_id, float("-inf")))
    if wait > 0:
        await event.reply(f"⏱ {int(wait) + 1} soniyadan keyin yuboring.")
        return
    last_request[event.sender_id] = now

    try:
        await send_stories(event, m.group(1), pinned)
    except Exception:
        log.exception("failed for %s", m.group(1))
        await event.reply("⚠️ Xatolik yuz berdi, keyinroq urinib ko'ring.")


def ask_phone() -> str:
    # Telethon treats any answer containing ':' as a bot token, which would
    # log the userbot in as the bot itself; only accept phone numbers here.
    while True:
        phone = input("Userbot akkaunt telefon raqami (+998...): ").strip()
        phone = re.sub(r"[\s()-]", "", phone)
        if re.fullmatch(r"\+\d{10,15}", phone):
            return phone
        print("Raqam to'liq va davlat kodi bilan bo'lsin, masalan: +998901234567")


async def main():
    # First run asks phone number + code in the terminal
    while True:
        try:
            await user.start(phone=ask_phone)
            break
        except PhoneNumberInvalidError:
            print("Telegram bu raqamni qabul qilmadi, qayta kiriting.")
    if (await user.get_me()).bot:
        raise SystemExit(
            "user_session.session bot sifatida kirgan. Faylni o'chirib, telefon raqam bilan qayta kiring."
        )
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    log.info("Bot @%s ishga tushdi", me.username)
    await bot.run_until_disconnected()


if __name__ == "__main__":
    user.loop.run_until_complete(main())
