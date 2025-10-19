import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

async def bilgilendirme(message):
    """
    Telegram bot üzerinden bildirim gönderir
    
    Args:
        message (str): Gönderilecek mesaj içeriği
    """
    # Telegram bot konfigürasyonu
    bot_token = "8016284721:AAE1pTh-n1InvD37rIfocdQZRpHuFBFlp4k"
    chat_id = "1145026697"
    
    # Bot oluştur ve mesaj gönder
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

if __name__ == "__main__":
    try:
        asyncio.run(bilgilendirme("selam ben senin asistanınım"))
    except KeyboardInterrupt:
        print("Bot durduruldu.")

