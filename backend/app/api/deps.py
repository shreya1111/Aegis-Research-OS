"""Shared FastAPI dependencies: settings, DB session, current user, services.

Every dependency here is a thin factory; business logic never lives in this
module (design §6.5). This is the single place request-scoped collaborators are
assembled, so services stay constructible without a request in unit tests.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import AgentDeps
from app.core.cache import (
    RateLimiter,
    TokenDenylist,
    get_rate_limiter,
    get_redis_client,
    get_token_denylist,
)
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.core.llm.provider import LLMProvider
from app.core.llm.registry import get_llm_provider
from app.db.models.user import User
from app.db.repositories.agent_trace_repository import AgentTraceRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_chunk_repository import DocumentChunkRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.project_memory_repository import ProjectMemoryRepository
from app.db.repositories.project_repository import ProjectRepository
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db_session
from app.services.agent_run_status import AgentRunStatusCache
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.external_sources.cache import ExternalSourceCache
from app.services.external_sources.external_source_service import ExternalSourceService
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService
from app.services.rag_service import RagService
from app.services.retrieval.reranker import CrossEncoderReranker
from app.services.retrieval.retrieval_service import RetrievalService

#: ``auto_error=False`` so a missing token surfaces as our own AuthenticationError
#: (mapped to the uniform envelope) rather than FastAPI's default 403 payload.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
TokenDenylistDep = Annotated[TokenDenylist, Depends(get_token_denylist)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
BearerTokenDep = Annotated[str | None, Depends(_oauth2_scheme)]


def get_user_repository(session: DbSessionDep) -> UserRepository:
    return UserRepository(session)


def get_project_repository(session: DbSessionDep) -> ProjectRepository:
    return ProjectRepository(session)


def get_document_repository(session: DbSessionDep) -> DocumentRepository:
    return DocumentRepository(session)


def get_document_chunk_repository(session: DbSessionDep) -> DocumentChunkRepository:
    return DocumentChunkRepository(session)


def get_conversation_repository(session: DbSessionDep) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(session: DbSessionDep) -> MessageRepository:
    return MessageRepository(session)


def get_agent_trace_repository(session: DbSessionDep) -> AgentTraceRepository:
    return AgentTraceRepository(session)


def get_project_memory_repository(session: DbSessionDep) -> ProjectMemoryRepository:
    return ProjectMemoryRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
ProjectRepositoryDep = Annotated[ProjectRepository, Depends(get_project_repository)]
DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
DocumentChunkRepositoryDep = Annotated[
    DocumentChunkRepository, Depends(get_document_chunk_repository)
]
ConversationRepositoryDep = Annotated[ConversationRepository, Depends(get_conversation_repository)]
MessageRepositoryDep = Annotated[MessageRepository, Depends(get_message_repository)]
AgentTraceRepositoryDep = Annotated[AgentTraceRepository, Depends(get_agent_trace_repository)]
ProjectMemoryRepositoryDep = Annotated[
    ProjectMemoryRepository, Depends(get_project_memory_repository)
]


def get_auth_service(
    user_repository: UserRepositoryDep,
    token_denylist: TokenDenylistDep,
    settings: SettingsDep,
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        token_denylist=token_denylist,
        settings=settings,
    )


def get_project_service(project_repository: ProjectRepositoryDep) -> ProjectService:
    return ProjectService(project_repository=project_repository)


def get_document_service(
    document_repository: DocumentRepositoryDep,
    settings: SettingsDep,
) -> DocumentService:
    return DocumentService(document_repository=document_repository, settings=settings)


def get_embedding_service_dep(settings: SettingsDep) -> EmbeddingService:
    return get_embedding_service(settings)


def get_llm_provider_dep(settings: SettingsDep) -> LLMProvider:
    return get_llm_provider(settings)


def get_reranker(settings: SettingsDep) -> CrossEncoderReranker | None:
    if not settings.retrieval_rerank_enabled:
        return None
    return CrossEncoderReranker(model_name=settings.retrieval_rerank_model)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service_dep)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider_dep)]
RerankerDep = Annotated[CrossEncoderReranker | None, Depends(get_reranker)]


def get_retrieval_service(
    chunk_repository: DocumentChunkRepositoryDep,
    embedding_service: EmbeddingServiceDep,
    reranker: RerankerDep,
    settings: SettingsDep,
) -> RetrievalService:
    return RetrievalService(
        chunk_repository=chunk_repository,
        embedding_service=embedding_service,
        reranker=reranker,
        top_k=settings.retrieval_top_k,
        top_n=settings.retrieval_top_n,
        rrf_k=settings.retrieval_rrf_k,
        rerank_enabled=settings.retrieval_rerank_enabled,
    )


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


def get_rag_service(
    retrieval_service: RetrievalServiceDep,
    llm_provider: LLMProviderDep,
    conversation_repository: ConversationRepositoryDep,
    message_repository: MessageRepositoryDep,
    trace_repository: AgentTraceRepositoryDep,
    settings: SettingsDep,
) -> RagService:
    return RagService(
        retrieval_service=retrieval_service,
        llm_provider=llm_provider,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        trace_repository=trace_repository,
        max_regeneration_attempts=settings.citation_max_regeneration_attempts,
    )


RagServiceDep = Annotated[RagService, Depends(get_rag_service)]


def get_external_source_cache(settings: SettingsDep) -> ExternalSourceCache:
    return ExternalSourceCache(
        get_redis_client(), ttl_seconds=settings.external_source_cache_ttl_seconds
    )


ExternalSourceCacheDep = Annotated[ExternalSourceCache, Depends(get_external_source_cache)]


def get_external_source_service(
    cache: ExternalSourceCacheDep, settings: SettingsDep
) -> ExternalSourceService:
    return ExternalSourceService(
        cache=cache,
        timeout_seconds=settings.external_source_timeout_seconds,
        max_results=settings.external_source_max_results,
        semantic_scholar_api_key=settings.semantic_scholar_api_key,
        core_api_key=settings.core_api_key,
    )


ExternalSourceServiceDep = Annotated[
    ExternalSourceService, Depends(get_external_source_service)
]


def get_memory_service(
    memory_repository: ProjectMemoryRepositoryDep,
    llm_provider: LLMProviderDep,
) -> MemoryService:
    return MemoryService(memory_repository=memory_repository, llm_provider=llm_provider)


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]


def get_agent_run_status_cache(settings: SettingsDep) -> AgentRunStatusCache:
    return AgentRunStatusCache(
        get_redis_client(), ttl_seconds=settings.agent_run_status_ttl_seconds
    )


AgentRunStatusCacheDep = Annotated[AgentRunStatusCache, Depends(get_agent_run_status_cache)]


def get_agent_deps(
    retrieval_service: RetrievalServiceDep,
    external_source_service: ExternalSourceServiceDep,
    llm_provider: LLMProviderDep,
    memory_service: MemoryServiceDep,
    trace_repository: AgentTraceRepositoryDep,
    settings: SettingsDep,
) -> AgentDeps:
    return AgentDeps(
        retrieval_service=retrieval_service,
        external_source_service=external_source_service,
        llm_provider=llm_provider,
        memory_service=memory_service,
        trace_repository=trace_repository,
        max_subtasks=settings.agent_max_subtasks,
        max_retries=settings.agent_max_retries,
    )


AgentDepsDep = Annotated[AgentDeps, Depends(get_agent_deps)]


def get_agent_service(
    deps: AgentDepsDep,
    conversation_repository: ConversationRepositoryDep,
    message_repository: MessageRepositoryDep,
    trace_repository: AgentTraceRepositoryDep,
    run_status_cache: AgentRunStatusCacheDep,
) -> AgentService:
    return AgentService(
        deps=deps,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        trace_repository=trace_repository,
        run_status_cache=run_status_cache,
    )


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


async def get_bearer_token(token: BearerTokenDep) -> str:
    """Extract the bearer token or raise ``AuthenticationError`` (design §6.2, FR-A6)."""
    if not token:
        raise AuthenticationError("Authentication is required.")
    return token


BearerTokenRequiredDep = Annotated[str, Depends(get_bearer_token)]


async def get_current_user(
    token: BearerTokenRequiredDep,
    auth_service: AuthServiceDep,
) -> User:
    """Resolve and return the authenticated caller.

    Every protected route depends on this — directly or via a project-scope
    dependency built on top of it (design §6.2).
    """
    return await auth_service.resolve_current_user(token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
