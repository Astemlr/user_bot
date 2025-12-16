"""Classic Bot для управления фильтрами и подписками."""
from pyrogram import Client, filters
from pyrogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session, init_db
from models import User, Filter, Subscription
from config import BOT_TOKEN, API_ID, API_HASH


class ClassicBot:
    """Classic Bot для управления через команды."""

    def __init__(self):
        """Инициализация Classic Bot."""
        self.client = Client(
            "classic_bot",
            bot_token=BOT_TOKEN,
            api_id=API_ID,
            api_hash=API_HASH
        )
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация всех обработчиков команд."""

        @self.client.on_message(filters.command("start"))
        async def start_handler(client: Client, message: Message):
            await self.handle_start(message)

        @self.client.on_message(filters.command("help"))
        async def help_handler(client: Client, message: Message):
            await self.handle_help(message)

        @self.client.on_message(filters.command("add_filter"))
        async def add_filter_handler(client: Client, message: Message):
            await self.handle_add_filter(message)

        @self.client.on_message(filters.command("add_topic"))
        async def add_topic_handler(client: Client, message: Message):
            await self.handle_add_topic(message)

        @self.client.on_message(filters.command("list_filters"))
        async def list_filters_handler(client: Client, message: Message):
            await self.handle_list_filters(message)

        @self.client.on_message(filters.command("delete_filter"))
        async def delete_filter_handler(client: Client, message: Message):
            await self.handle_delete_filter(message)

        @self.client.on_message(filters.command("add_subscription"))
        async def add_subscription_handler(client: Client, message: Message):
            await self.handle_add_subscription(message)

        @self.client.on_message(filters.command("list_subscriptions"))
        async def list_subscriptions_handler(client: Client, message: Message):
            await self.handle_list_subscriptions(message)

        @self.client.on_message(filters.command("remove_subscription"))
        async def remove_subscription_handler(client: Client, message: Message):
            await self.handle_remove_subscription(message)

        @self.client.on_message(filters.command("set_target_chat"))
        async def set_target_chat_handler(client: Client, message: Message):
            await self.handle_set_target_chat(message)

    async def handle_start(self, message: Message):
        """Обработка команды /start."""
        user_id = message.from_user.id
        username = message.from_user.username

        async for session in get_session():
            user_query = select(User).where(User.user_id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id, username=username)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            welcome_text = (
                "Привет! Я бот для агрегации новостей.\n\n"
                "Используй команды:\n"
                "/help - справка по командам\n"
                "/add_filter <ключевые слова> - добавить фильтр по ключевым словам\n"
                "/add_topic <тема> - добавить тему для семантического поиска\n"
                "/list_filters - список всех фильтров\n"
                "/delete_filter <id> - удалить фильтр\n"
                "/add_subscription <username или ID> - добавить подписку на канал/чат\n"
                "/list_subscriptions - список подписок\n"
                "/remove_subscription <id> - удалить подписку\n"
                "/set_target_chat - установить целевой чат для пересылки"
            )
            await message.reply_text(welcome_text)

    async def handle_help(self, message: Message):
        """Обработка команды /help."""
        help_text = (
            "Доступные команды:\n\n"
            "Фильтры:\n"
            "/add_filter <ключевые слова через запятую> - добавить фильтр\n"
            "/add_topic <тема> - добавить тему для семантического поиска\n"
            "/list_filters - показать все фильтры\n"
            "/delete_filter <id> - удалить фильтр\n\n"
            "Подписки:\n"
            "/add_subscription <username или ID> - подписаться на канал/чат\n"
            "/list_subscriptions - показать все подписки\n"
            "/remove_subscription <id> - отписаться\n\n"
            "Настройки:\n"
            "/set_target_chat - установить чат для пересылки сообщений"
        )
        await message.reply_text(help_text)

    async def handle_add_filter(self, message: Message):
        """Обработка команды /add_filter."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        if len(command_parts) < 2:
            await message.reply_text("Использование: /add_filter <ключевые слова через запятую>")
            return

        keywords = command_parts[1]

        async for session in get_session():
            user_query = select(User).where(User.user_id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id, username=message.from_user.username)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            new_filter = Filter(
                user_id=user_id,
                keywords=keywords,
                use_semantic=False
            )
            session.add(new_filter)
            await session.commit()

            await message.reply_text(f"Фильтр добавлен! ID: {new_filter.id}")

    async def handle_add_topic(self, message: Message):
        """Обработка команды /add_topic."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        if len(command_parts) < 2:
            await message.reply_text("Использование: /add_topic <тема>")
            return

        topic = command_parts[1]

        async for session in get_session():
            user_query = select(User).where(User.user_id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id, username=message.from_user.username)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            new_filter = Filter(
                user_id=user_id,
                topics=topic,
                use_semantic=True
            )
            session.add(new_filter)
            await session.commit()

            await message.reply_text(f"Тема добавлена для семантического поиска! ID: {new_filter.id}")

    async def handle_list_filters(self, message: Message):
        """Обработка команды /list_filters."""
        user_id = message.from_user.id

        async for session in get_session():
            filters_query = select(Filter).where(Filter.user_id == user_id)
            result = await session.execute(filters_query)
            filters = result.scalars().all()

            if not filters:
                await message.reply_text("У вас пока нет фильтров.")
                return

            filters_text = "Ваши фильтры:\n\n"
            for f in filters:
                filter_type = "Семантика" if f.use_semantic else "Ключевые слова"
                if f.use_semantic:
                    content = f.topics if f.topics else "(пусто)"
                else:
                    content = f.keywords if f.keywords else "(пусто)"
                filters_text += f"ID: {f.id} | {filter_type}: {content}\n"

            await message.reply_text(filters_text)

    async def handle_delete_filter(self, message: Message):
        """Обработка команды /delete_filter."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        if len(command_parts) < 2:
            await message.reply_text("Использование: /delete_filter <id>")
            return

        try:
            filter_id = int(command_parts[1])
        except ValueError:
            await message.reply_text("ID должен быть числом.")
            return

        async for session in get_session():
            filter_query = select(Filter).where(
                Filter.id == filter_id,
                Filter.user_id == user_id
            )
            result = await session.execute(filter_query)
            filter_obj = result.scalar_one_or_none()

            if not filter_obj:
                await message.reply_text("Фильтр не найден.")
                return

            await session.delete(filter_obj)
            await session.commit()

            await message.reply_text(f"Фильтр {filter_id} удален.")

    async def handle_add_subscription(self, message: Message):
        """Обработка команды /add_subscription."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        if len(command_parts) < 2:
            await message.reply_text("Использование: /add_subscription <username или ID>")
            return

        chat_identifier = command_parts[1].strip()

        async for session in get_session():
            user_query = select(User).where(User.user_id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id, username=message.from_user.username)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            try:
                chat_id = None
                chat_title = "Unknown"
                
                if chat_identifier.startswith("@"):
                    try:
                        chat = await self.client.get_chat(chat_identifier)
                        chat_id = chat.id
                        chat_title = chat.title or chat.first_name or chat_identifier
                    except Exception as e:
                        await message.reply_text(
                            f"Не удалось получить информацию о {chat_identifier}.\n"
                            f"Убедитесь, что Classic Bot имеет доступ к этому чату, или используйте числовой ID."
                        )
                        return
                else:
                    try:
                        chat_id = int(chat_identifier.strip())
                        chat_title = f"Chat {chat_id}"
                        
                        try:
                            chat = await self.client.get_chat(chat_id)
                            chat_title = chat.title or chat.first_name or f"Chat {chat_id}"
                        except Exception:
                            pass
                            
                    except ValueError:
                        await message.reply_text(
                            "Неверный формат. Используйте:\n"
                            "- @username для каналов/групп с username\n"
                            "- Числовой ID (например: -4866333469 для групп)"
                        )
                        return

                existing_query = select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.chat_id == chat_id
                )
                existing_result = await session.execute(existing_query)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    await message.reply_text("Вы уже подписаны на этот канал/чат.")
                    return

                if chat_id < 0:
                    chat_type = "group"
                else:
                    chat_type = "channel" if abs(chat_id) > 1000000000000 else "private"

                subscription = Subscription(
                    user_id=user_id,
                    chat_id=chat_id,
                    chat_title=chat_title,
                    chat_type=chat_type
                )
                session.add(subscription)
                await session.commit()

                await message.reply_text(
                    f"Подписка добавлена: {chat_title} (ID: {subscription.id})\n"
                    f"Убедитесь, что User Bot является участником группы с ID {chat_id}"
                )

            except Exception as e:
                await message.reply_text(f"Ошибка при добавлении подписки: {str(e)}")

    async def handle_list_subscriptions(self, message: Message):
        """Обработка команды /list_subscriptions."""
        user_id = message.from_user.id

        async for session in get_session():
            subscriptions_query = select(Subscription).where(Subscription.user_id == user_id)
            result = await session.execute(subscriptions_query)
            subscriptions = result.scalars().all()

            if not subscriptions:
                await message.reply_text("У вас пока нет подписок.")
                return

            subscriptions_text = "Ваши подписки:\n\n"
            for sub in subscriptions:
                subscriptions_text += f"ID: {sub.id} | {sub.chat_title} ({sub.chat_type})\n"

            await message.reply_text(subscriptions_text)

    async def handle_remove_subscription(self, message: Message):
        """Обработка команды /remove_subscription."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        if len(command_parts) < 2:
            await message.reply_text("Использование: /remove_subscription <id>")
            return

        try:
            subscription_id = int(command_parts[1])
        except ValueError:
            await message.reply_text("ID должен быть числом.")
            return

        async for session in get_session():
            subscription_query = select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id
            )
            result = await session.execute(subscription_query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                await message.reply_text("Подписка не найдена.")
                return

            chat_title = subscription.chat_title
            await session.delete(subscription)
            await session.commit()

            await message.reply_text(f"Подписка '{chat_title}' удалена.")

    async def handle_set_target_chat(self, message: Message):
        """Обработка команды /set_target_chat."""
        user_id = message.from_user.id
        command_parts = message.text.split(maxsplit=1)

        target_chat_id = None

        if len(command_parts) > 1:
            chat_identifier = command_parts[1].strip()
            try:
                target_chat_id = int(chat_identifier)
            except ValueError:
                await message.reply_text(
                    "Неверный формат ID. Используйте числовой ID (например: -4720266687)\n"
                    "Или отправьте команду без параметра в нужном чате."
                )
                return
        elif message.reply_to_message:
            target_chat_id = message.reply_to_message.chat.id
        else:
            target_chat_id = message.chat.id

        async for session in get_session():
            user_query = select(User).where(User.user_id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id, username=message.from_user.username)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            user.target_chat_id = target_chat_id
            await session.commit()

            await message.reply_text(f"Целевой чат установлен: {target_chat_id}")

    async def start(self):
        """Запуск classic bot."""
        await init_db()
        await self.client.start()
        print("Classic Bot запущен")

    async def stop(self):
        """Остановка classic bot."""
        await self.client.stop()
        print("Classic Bot остановлен")

    def run(self):
        """Запуск classic bot в цикле событий."""
        self.client.run(self.start())
