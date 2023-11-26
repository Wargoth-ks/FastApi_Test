import sys
import os

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from source.conf.configs import settings


engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL_LOCAL, echo=True)  # type: ignore

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# async def init_db():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """
    The get_session function is a context manager that creates an async session
        and returns it to the caller.  The caller can then use this session to perform
        database operations.  When the caller is done with the session, they should close it.

    :return: A context manager that handles the session for you
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await session.close()
