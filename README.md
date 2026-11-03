# tg-story-bot

Botga `@username` yuborasiz — o'sha odamning aktiv storylarini qaytaradi. Story "ko'rildi" deb belgilanmaydi.

## Qanday ishlaydi

Bot API storylarni o'qiy olmaydi, shuning uchun ikkita client bor:

- **bot** (`BOT_TOKEN`) — xabarlarni qabul qiladi va fayllarni yuboradi;
- **userbot** (oddiy Telegram akkaunt) — `stories.getPeerStories` orqali storylarni oladi va yuklab beradi. `readStories` chaqirilmaydi, shuning uchun ko'rganlar ro'yxatiga tushmaydi.

Faqat userbot akkauntiga ko'rinadigan storylar olinadi (odatda "Hamma"ga ochiq bo'lganlari). "Yaqin do'stlar" yoki yashirilgan storylar chiqmaydi.

## O'rnatish

1. https://my.telegram.org → API development tools → `API_ID`, `API_HASH`.
2. @BotFather → yangi bot → `BOT_TOKEN`.
3. `.env.example` ni `.env` ga nusxalab, qiymatlarni to'ldiring. `ALLOWED_IDS` ga o'z ID ingizni yozing (@userinfobot dan bilib olasiz).
4. ```bash
   python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
   ```
5. ```bash
   python bot.py
   ```
   Birinchi ishga tushganda userbot uchun telefon raqam va kod so'raladi; `user_session.session` fayli yaratiladi — uni hech kimga bermang.

## Buyruqlar

- `@username` yoki `t.me/username` — aktiv storylar (10 tadan albom qilib yuboriladi)
- `/pinned @username` — profilga pin qilingan storylar

Bitta foydalanuvchi `COOLDOWN` soniyada (standart 10) bir marta so'rov yubora oladi.

## Serverga qo'yish

### systemd (VPS)

1. Repo'ni serverga clone qiling, `.env` ni to'ldiring, venv yarating (yuqoridagi 4-qadam).
2. Bir marta qo'lda `python bot.py` ishga tushirib, userbot'ga kiring, keyin Ctrl+C.
3. `deploy/tg-story-bot.service` dagi `USER` va `/path/to/tg-story-bot` ni almashtirib:
   ```bash
   sudo cp deploy/tg-story-bot.service /etc/systemd/system/
   sudo systemctl enable --now tg-story-bot
   journalctl -u tg-story-bot -f
   ```

### Docker

```bash
docker compose run --rm bot      # birinchi marta: telefon raqam + kod, keyin Ctrl+C
docker compose up -d --build
```

Session fayllari `sessions/` papkasida saqlanadi.

## Maslahat

Userbot uchun asosiy akkauntingizni emas, alohida akkaunt ishlating: ko'p so'rov yuborilsa Telegram vaqtincha cheklashi mumkin.
