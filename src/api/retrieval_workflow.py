"""Coldline.

===================

File:              src/api/retrieval_workflow.py
Component:         API — Retrieval workflow
Purpose:           Turn one procedural question into ranked evidence and prompt context.
Interacts With:    The Retriever port, domain contracts, and the retrieval route
Sprint/Task:       Sprint 2 — Project 2
Concepts:          Application coordination, context assembly, coupling
Tools:             Python 3.12
"""

from dataclasses import dataclass

from domain.contracts import (
    AssembledContext,
    AuthorizationContext,
    Candidate,
    RetrievalRequest,
    RetrievalResult,
)
from ports import Retriever

CITATION_LIMIT = 3


@dataclass(frozen=True)
class RetrievalOutcome:
    """Carry both halves of one answered question."""

    result: RetrievalResult
    context: AssembledContext


class RetrievalWorkflow:
    """Coordinate retrieval and build prompt context in one place.

    Two distinct responsibilities live in this single class:

    - *Retrieval orchestration* resolves the controlled parameters, builds the
      request with the caller's authorization context, invokes the port, and
      selects the citation-eligible candidates from the fused ranking.
    - *Context assembly* trims the selected chunk texts to the token budget,
      formats the prompt block, and produces the citation strings.

    They are interleaved deliberately. Changing the token budget means editing
    the same method that decides how many candidates the ranking contributes,
    and testing the selection rule means constructing the whole workflow. That
    coupling is the subject of Task 2.2, which extracts one of the two
    responsibilities behind an internal boundary.
    """

    def __init__(
        self,
        retriever: Retriever,
        *,
        top_k: int,
        dense_weight: float,
        token_budget: int,
        citation_limit: int = CITATION_LIMIT,
    ) -> None:
        """Receive the retrieval port and the supplied retrieval parameters."""
        if citation_limit < 1:
            raise ValueError("citation_limit must be at least 1")
        self._retriever = retriever
        self._top_k = top_k
        self._dense_weight = dense_weight
        self._token_budget = token_budget
        self._citation_limit = citation_limit

    async def answer(
        self,
        query_id: str,
        text: str,
        authorization: AuthorizationContext,
        *,
        explain: bool = False,
    ) -> RetrievalOutcome:
        """Retrieve evidence for one question and assemble its prompt context."""
        request = RetrievalRequest(
            query_id=query_id,
            text=text,
            authorization=authorization,
            top_k=self._top_k,
            dense_weight=self._dense_weight,
            explain=explain,
        )
        result = await self._retriever.search_hybrid(request)

        # One document must not fill the whole context, so only its
        # best-ranked chunk is eligible; the cap then applies to documents.
        selected: list[Candidate] = []
        seen_documents: set[str] = set()
        for candidate in result.results:
            if candidate.document_id in seen_documents:
                continue
            seen_documents.add(candidate.document_id)
            selected.append(candidate)
            if len(selected) == self._citation_limit:
                break

        # The budget is a whole-word count, not a model tokenizer's count. It
        # is a deterministic local stand-in and no claim about a hosted
        # model's context accounting follows from it.
        blocks: list[str] = []
        citations: list[str] = []
        used = 0
        for candidate in selected:
            words = candidate.text.split()
            remaining = self._token_budget - used
            if remaining <= 0:
                break
            trimmed = " ".join(words[:remaining])
            used += len(trimmed.split())
            blocks.append(f"[{candidate.chunk_id}] {trimmed}")
            citations.append(
                f"{candidate.document_id}@{candidate.provenance_revision}"
                f" ({candidate.access.tenant_id}/{candidate.access.access_tier.value})"
            )
        context = AssembledContext(
            query_id=query_id,
            prompt_context="\n\n".join(blocks),
            citations=tuple(citations),
            token_budget=self._token_budget,
            used_tokens=used,
        )
        return RetrievalOutcome(result=result, context=context)
