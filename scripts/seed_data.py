import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.providers.factory import get_llm_provider
from backend.app.context.builder import ContextBuilder
from backend.app.exemplars.store import ExemplarStore


async def seed():
    print("Seeding Kifayat database...")
    store = SQLiteStore(db_path=settings.SQLITE_DB_PATH)
    context_builder = ContextBuilder(handbook_path=settings.HANDBOOK_PATH)
    provider = get_llm_provider(handbook_text=context_builder.canonical_handbook)
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    await exemplar_store.seed_defaults(seed_file=settings.SEED_EXEMPLARS_PATH)
    print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
