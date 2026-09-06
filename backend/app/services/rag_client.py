"""RAG client — used by the FastAPI backend to call the RAG engine."""

from __future__ import annotations

from typing import Any, Optional

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_RAG_BASE = f"http://{settings.RAG_HOST}:{settings.RAG_PORT}"
_TIMEOUT = 15.0


async def retrieve_policy(
    query: str,
    top_k: int = 5,
    exam_id: Optional[str] = None,
    institution: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieve relevant policy chunks from the RAG engine."""
    payload: dict[str, Any] = {"query": query, "top_k": top_k}
    if exam_id:
        payload["exam_id"] = exam_id
    if institution:
        payload["institution"] = institution
    if doc_type:
        payload["doc_type"] = doc_type

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_RAG_BASE}/retrieve", json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info("rag_retrieved", results=data.get("result_count", 0))
            return data.get("results", [])
    except Exception as exc:
        logger.error("rag_retrieve_failed", error=str(exc))
        return []


async def get_policy_context(
    exam_id: Optional[str] = None,
    institution: Optional[str] = None,
) -> str:
    """Get the combined policy context string for AI prompts."""
    params: dict[str, str] = {}
    if exam_id:
        params["exam_id"] = exam_id
    if institution:
        params["institution"] = institution

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_RAG_BASE}/policy-context",
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("policy_context", "")
    except Exception as exc:
        logger.error("rag_policy_context_failed", error=str(exc))
        return (
            "Policy context unavailable. "
            "Default: AI assistants are prohibited during closed-resource examinations."
        )
