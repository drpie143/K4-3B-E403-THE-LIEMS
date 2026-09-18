from __future__ import annotations

from dataclasses import dataclass, field

from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings, get_settings
from app.repository.cards import CardRepository, get_card_repository
from app.repository.conversation import ConversationRepository
from app.repository.postgres import PostgresConversationRepository
from app.repository.qdrant import connect_qdrant
from app.repository.redis_store import ping_redis
from app.repository.retriever import LectureRetriever
from app.repository.vector import MemoryVectorStore
from app.service.agent.graph import build_graph
from app.service.agent.runtime import Runtime, set_runtime
from app.service.ai.service import AIService
from app.service.chat import ChatService
from app.service.profile import ProfileService
from app.service.vlearn import VLearnService


@dataclass
class AppContainer:
    settings: Settings
    repository: object
    ai: AIService
    retriever: LectureRetriever
    graph: object
    chat: ChatService
    profile: ProfileService
    cards: CardRepository
    vlearn: VLearnService
    storage_kind: str = "memory"
    vector_kind: str = "memory"
    redis_ok: bool = False
    _closers: list = field(default_factory=list)

    async def aclose(self) -> None:
        await self.ai.aclose()
        for fn in self._closers:
            await fn()


def _assemble(
    settings: Settings,
    repository,
    vector,
    *,
    storage_kind: str,
    vector_kind: str,
    redis_ok: bool,
    closers: list | None = None,
) -> AppContainer:
    ai = AIService(settings)
    retriever = LectureRetriever(vector, ai.embed)
    set_runtime(
        Runtime(
            settings=settings,
            repository=repository,
            retriever=retriever,
            ai=ai,
        )
    )
    graph = build_graph(MemorySaver())
    chat = ChatService(repository, graph, settings)
    cards = get_card_repository()
    return AppContainer(
        settings=settings,
        repository=repository,
        ai=ai,
        retriever=retriever,
        graph=graph,
        chat=chat,
        profile=ProfileService(repository),
        cards=cards,
        vlearn=VLearnService(chat, repository, cards),
        storage_kind=storage_kind,
        vector_kind=vector_kind,
        redis_ok=redis_ok,
        _closers=closers or [],
    )


def build_container(settings: Settings | None = None) -> AppContainer:
    """Sync path — memory store, dùng cho pytest / CLI."""
    settings = settings or get_settings()
    return _assemble(
        settings,
        ConversationRepository(lease_seconds=settings.lease_seconds),
        MemoryVectorStore(settings.embedding_dim),
        storage_kind="memory",
        vector_kind="memory",
        redis_ok=False,
    )


async def build_container_async(settings: Settings | None = None) -> AppContainer:
    """Lifespan: Postgres / Qdrant / Redis nếu cấu hình và kết nối được, không thì fallback."""
    settings = settings or get_settings()
    closers: list = []
    storage_kind = "memory"
    repository: object = ConversationRepository(lease_seconds=settings.lease_seconds)
    if settings.storage == "postgres" and settings.database_url:
        try:
            pg = await PostgresConversationRepository.connect(
                settings.database_url, settings.lease_seconds
            )
            repository = pg
            storage_kind = "postgres"
            closers.append(pg.aclose)
        except Exception:
            storage_kind = "memory"

    vector_kind = "memory"
    vector: object = MemoryVectorStore(settings.embedding_dim)
    if settings.vector_backend == "qdrant":
        q = await connect_qdrant(settings.qdrant_url, settings.embedding_dim)
        if q is not None:
            vector = q
            vector_kind = "qdrant"

    redis_ok = False
    if settings.checkpointer == "redis" and settings.redis_url:
        redis_ok = await ping_redis(settings.redis_url)

    return _assemble(
        settings,
        repository,
        vector,
        storage_kind=storage_kind,
        vector_kind=vector_kind,
        redis_ok=redis_ok,
        closers=closers,
    )
