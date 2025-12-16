"""User Bot для мониторинга сообщений и пересылки."""
import asyncio
import time
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import PeerFlood, FloodWait
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session, init_db
from models import User, Filter, Subscription
from filter_engine import FilterEngine
from config import API_ID, API_HASH


class UserBot:
    """User Bot для мониторинга сообщений из подписок."""

    def __init__(self):
        """Инициализация User Bot."""
        self.client = Client(
            "user_bot_session",
            api_id=API_ID,
            api_hash=API_HASH
        )
        self.filter_engine = FilterEngine()
        self.last_forward_time = {}
        self.min_forward_interval = 2

    async def start(self):
        """Запуск user bot."""
        await init_db()
        await self.client.start()
        
        me = await self.client.get_me()
        print(f"User Bot запущен как: {me.first_name} (@{me.username or 'без username'})")
        print(f"User Bot ID: {me.id}")
        print("User Bot будет мониторить только группы и каналы (не личные чаты)")
        
        async for session in get_session():
            try:
                subscriptions_query = select(Subscription)
                result = await session.execute(subscriptions_query)
                subscriptions = result.scalars().all()
                if subscriptions:
                    print(f"\nАктивные подписки ({len(subscriptions)}):")
                    for sub in subscriptions:
                        print(f"   - {sub.chat_title} (ID: {sub.chat_id})")
                else:
                    print("\nНет активных подписок. Добавьте подписку через Classic Bot: /add_subscription")
            finally:
                pass

        print("Регистрирую обработчик сообщений...")
        
        @self.client.on_message()
        async def handle_message(client: Client, message: Message):
            chat_id = message.chat.id if message.chat else None
            chat_type = message.chat.type if message.chat else None
            chat_title = message.chat.title if message.chat else "Unknown"
            has_text = bool(message.text or message.caption)
            from_user = message.from_user.username if message.from_user else "unknown"
            
            print(f"[DEBUG] Событие: chat={chat_id} ({chat_title}), type={chat_type}, from=@{from_user}, text={has_text}")
            
            await self.process_message(message)
        
        print("Обработчик зарегистрирован")

    async def process_message(self, message: Message):
        """Обработка входящего сообщения."""
        if not message.text and not message.caption:
            print(f"Пропущено: нет текста")
            return

        chat_id = message.chat.id if message.chat else None
        if not chat_id:
            print(f"Пропущено: нет chat_id")
            return

        chat_type = message.chat.type if message.chat else None
        
        if chat_id > 0:
            print(f"Пропущено: личный чат (ID: {chat_id})")
            return

        if message.from_user and message.from_user.is_bot:
            print(f"Пропущено: сообщение от бота")
            return

        text = message.text or message.caption or ""
        chat_title = message.chat.title if message.chat else "Unknown"
        print(f"ОБРАБОТКА: группа '{chat_title}' (ID: {chat_id}, тип: {chat_type})")
        print(f"Текст: {text[:100]}...")

        async for session in get_session():
            try:
                subscriptions_query = select(Subscription).where(Subscription.chat_id == chat_id)
                result = await session.execute(subscriptions_query)
                subscriptions = result.scalars().all()

                if not subscriptions:
                    print(f"Нет подписок на чат {chat_id}")
                    return
                
                print(f"Найдено подписок: {len(subscriptions)}")

                for subscription in subscriptions:
                    user_id = subscription.user_id

                    user_query = select(User).where(User.user_id == user_id)
                    user_result = await session.execute(user_query)
                    user = user_result.scalar_one_or_none()

                    if not user:
                        continue

                    filters_query = select(Filter).where(Filter.user_id == user_id)
                    filters_result = await session.execute(filters_query)
                    filters = filters_result.scalars().all()

                    if not filters:
                        print(f"У пользователя {user_id} нет фильтров")
                        continue

                    print(f"У пользователя {user_id} найдено фильтров: {len(filters)}")

                    filter_dicts = []
                    print(f"Применяю фильтры:")
                    for f in filters:
                        filter_info = {
                            "keywords": f.keywords,
                            "topics": f.topics,
                            "use_semantic": f.use_semantic
                        }
                        filter_dicts.append(filter_info)
                        
                        if f.use_semantic:
                            print(f"   - ID {f.id}: Семантика '{f.topics}'")
                        else:
                            print(f"   - ID {f.id}: Ключевые слова '{f.keywords}'")

                    should_forward = self.filter_engine.should_forward(text, filter_dicts)
                    print(f"Результат фильтрации: {'ПЕРЕСЛАТЬ' if should_forward else 'не соответствует фильтрам'}")
                    
                    if should_forward:
                        await self.forward_message(user, message)
            finally:
                pass

    async def forward_message(self, user: User, message: Message):
        """Пересылка сообщения в целевой чат пользователя."""
        if not user.target_chat_id:
            target_chat_id = user.user_id
            print(f"Целевой чат не установлен, отправляю в личные сообщения: {target_chat_id}")
        else:
            target_chat_id = user.target_chat_id
            print(f"Отправляю в целевой чат: {target_chat_id}")

        current_time = time.time()
        if target_chat_id in self.last_forward_time:
            time_since_last = current_time - self.last_forward_time[target_chat_id]
            if time_since_last < self.min_forward_interval:
                wait_time = self.min_forward_interval - time_since_last
                print(f"Задержка {wait_time:.1f} сек для избежания лимита...")
                await asyncio.sleep(wait_time)

        try:
            await message.forward(chat_id=target_chat_id)
            self.last_forward_time[target_chat_id] = time.time()
            print(f"Сообщение успешно переслано в чат {target_chat_id}")
        except FloodWait as e:
            wait_time = e.value
            print(f"Telegram просит подождать {wait_time} секунд...")
            await asyncio.sleep(wait_time)
            try:
                await message.forward(chat_id=target_chat_id)
                self.last_forward_time[target_chat_id] = time.time()
                print(f"Сообщение переслано после ожидания")
            except Exception as retry_error:
                print(f"Ошибка при повторной пересылке: {retry_error}")
        except PeerFlood:
            print(f"PEER_FLOOD: Аккаунт временно ограничен из-за частых пересылок")
            print(f"Подождите несколько минут или используйте другой целевой чат")
        except Exception as e:
            print(f"Ошибка при пересылке сообщения: {e}")
            if "PEER_FLOOD" not in str(e) and "FLOOD" not in str(e):
                import traceback
                traceback.print_exc()

    async def stop(self):
        """Остановка user bot."""
        await self.client.stop()
        print("User Bot остановлен")

    def run(self):
        """Запуск user bot в цикле событий."""
        self.client.run(self.start())

