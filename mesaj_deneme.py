# main.py
import asyncio
from telegram_bot import send_message

async def main(message: str):
    await send_message(message)

if __name__ == "__main__":
    asyncio.run(main("hello"))
