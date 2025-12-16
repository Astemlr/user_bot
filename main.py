"""Точка входа для запуска обоих ботов."""
import asyncio
import sys
from pyrogram import idle
from user_bot import UserBot
from classic_bot import ClassicBot
from config import validate_config


async def main():
    """Запуск обоих ботов одновременно."""
    if not validate_config():
        print("\nИсправьте ошибки в .env файле и попробуйте снова.")
        sys.exit(1)
    
    user_bot = UserBot()
    classic_bot = ClassicBot()

    try:
        await user_bot.start()
        await classic_bot.start()

        print("Оба бота запущены. Нажмите Ctrl+C для остановки.")
        
        await idle()

    except KeyboardInterrupt:
        print("\nОстановка ботов...")
        await user_bot.stop()
        await classic_bot.stop()
        print("Боты остановлены.")


if __name__ == "__main__":
    asyncio.run(main())

