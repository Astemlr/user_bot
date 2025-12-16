"""Скрипт для инициализации базы данных."""
import asyncio
import sys
from sqlalchemy import text
from database import engine, Base
from config import DATABASE_URL
from models import User, Filter, Subscription


async def create_database():
    """Создание базы данных, если её нет."""
    try:
        db_url_parts = DATABASE_URL.replace("postgresql+asyncpg://", "").split("/")
        if len(db_url_parts) < 2:
            print("Неверный формат DATABASE_URL")
            return False
        
        db_name = db_url_parts[-1]
        base_url = "/".join(db_url_parts[:-1])
        postgres_url = f"postgresql+asyncpg://{base_url}/postgres"
        
        print(f"Проверяю существование базы данных '{db_name}'...")
        
        from sqlalchemy.ext.asyncio import create_async_engine
        postgres_engine = create_async_engine(postgres_url, echo=False)
        
        async with postgres_engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            exists = result.scalar()
        
        if not exists:
            print(f"Создаю базу данных '{db_name}'...")
            async with postgres_engine.connect() as conn:
                await conn.execute(text("COMMIT"))
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                await conn.commit()
            print(f"База данных '{db_name}' создана!")
        else:
            print(f"База данных '{db_name}' уже существует")
        
        await postgres_engine.dispose()
        return True
        
    except Exception as e:
        print(f"Ошибка при создании базы данных: {e}")
        print("\nУбедитесь, что:")
        print("   1. PostgreSQL запущен")
        print("   2. DATABASE_URL в .env файле правильный")
        print("   3. У пользователя есть права на создание БД")
        return False


async def create_tables():
    """Создание всех таблиц в базе данных."""
    try:
        print("Создаю таблицы...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Таблицы созданы успешно!")
        
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = result.fetchall()
            if tables:
                print(f"Создано таблиц: {len(tables)}")
                for table in tables:
                    print(f"   - {table[0]}")
        
        return True
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция инициализации."""
    print("Инициализация базы данных...\n")
    
    if not await create_database():
        sys.exit(1)
    
    print()
    
    if not await create_tables():
        sys.exit(1)
    
    print("\nБаза данных готова к использованию!")


if __name__ == "__main__":
    asyncio.run(main())

