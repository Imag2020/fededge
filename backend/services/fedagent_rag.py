"""
FedAgent RAG Service - RAG avec FedAgent (sans DSPy)
Intègre la recherche vectorielle avec ChatWorker de FedAgent
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .rag_news import search_news, EvidenceCard
from ..fedagent_service import get_chat_worker, is_initialized
from ..db.crud import get_world_context_for_llm, get_market_context_for_llm
from ..db.models import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from RAG chat system"""
    answer: str
    sources: List[Dict[str, Any]]
    cards: List[EvidenceCard]
    confidence: float
    is_rag_response: bool
    latency_ms: float


class IntentionRouter:
    """
    Routes user questions to appropriate response systems
    Detects crypto/news-related queries that should use RAG
    """

    def __init__(self):
        # Keywords that suggest crypto/news intent
        self.crypto_keywords = {
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'defi', 'nft', 'trading', 'price', 'market',
            'bull', 'bear', 'pump', 'dump', 'hodl', 'altcoin', 'satoshi',
            'solana', 'sol', 'cardano', 'ada', 'polkadot', 'dot', 'chainlink',
            'regulation', 'sec', 'etf', 'institutional', 'adoption'
        }

        # Question patterns that suggest news/context queries
        self.news_patterns = [
            r'\b(what|why|how|when|where)\b.*\b(happen|news|recent|latest)\b',
            r'\bwhat.*\b(sentiment|market|trend|outlook)\b',
            r'\bwhy.*\b(price|move|up|down|crash|moon)\b',
            r'\b(explain|tell me about|what about)\b',
            r'\b(regulation|policy|government|ban)\b',
            r'\b(pourquoi|comment|que se passe|actualité|nouvelles)\b',  # French
        ]

        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.news_patterns]

    def should_use_rag(self, query: str) -> Tuple[bool, float]:
        """
        Determine if query should use RAG system

        Args:
            query: User query string

        Returns:
            (should_use_rag, confidence_score)
        """
        query_lower = query.lower()
        score = 0.0

        # Check for crypto keywords (40% weight)
        crypto_matches = sum(1 for keyword in self.crypto_keywords if keyword in query_lower)
        if crypto_matches > 0:
            score += min(0.4, crypto_matches * 0.1)

        # Check for news/question patterns (30% weight)
        pattern_matches = sum(1 for pattern in self.compiled_patterns if pattern.search(query))
        if pattern_matches > 0:
            score += min(0.3, pattern_matches * 0.15)

        # Check query structure (30% weight)
        if any(word in query_lower for word in ['?', 'what', 'why', 'how', 'when', 'explain']):
            score += 0.15

        if any(word in query_lower for word in ['recent', 'latest', 'news', 'update', 'currently']):
            score += 0.15

        # Use RAG if confidence > 0.3
        should_use = score > 0.3

        return should_use, score


class FedAgentRagService:
    """
    FedAgent RAG service - Simplifié sans DSPy
    Utilise ChatWorker pour la génération de réponses avec contexte RAG
    """

    def __init__(self):
        self.intention_router = IntentionRouter()
        self.max_context_tokens = 2000  # Limite de tokens pour le contexte RAG

    def _build_rag_context(
        self,
        query: str,
        cards: List[EvidenceCard],
        world_context: Optional[str] = None,
        market_context: Optional[str] = None
    ) -> str:
        """Construit le contexte RAG pour le prompt"""

        context_parts = []

        # Ajouter le contexte monde si disponible
        if world_context:
            context_parts.append(f"## World Context\n{world_context}\n")

        # Ajouter le contexte marché si disponible
        if market_context:
            context_parts.append(f"## Market Context\n{market_context}\n")

        # Ajouter les sources RAG
        if cards:
            context_parts.append("## Relevant News Articles\n")
            for i, card in enumerate(cards[:5], 1):  # Max 5 cards
                context_parts.append(
                    f"[{i}] {card.title}\n"
                    f"Source: {card.source} | Date: {card.published_at}\n"
                    f"{card.passage}\n"
                    f"URL: {card.url}\n"
                )

        return "\n".join(context_parts)

    async def process_chat_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        force_rag: bool = False,
        use_mcp_tools: bool = False,
        conversation_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat message with optional RAG

        Args:
            message: User message
            conversation_history: Previous messages
            force_rag: Force use of RAG even if intention router says no
            use_mcp_tools: Enable MCP tools (not implemented yet)
            conversation_id: Conversation ID for tracking

        Returns:
            ChatResponse with answer and sources
        """
        start_time = time.time()

        # Check if FedAgent is initialized
        if not is_initialized():
            logger.error("FedAgent not initialized")
            return ChatResponse(
                answer="Le système n'est pas encore initialisé. Veuillez réessayer dans quelques instants.",
                sources=[],
                cards=[],
                confidence=0.0,
                is_rag_response=False,
                latency_ms=0
            )

        # Determine if RAG should be used
        should_use_rag, confidence = self.intention_router.should_use_rag(message)
        use_rag = force_rag or should_use_rag

        cards = []
        sources = []
        rag_context = ""

        if use_rag:
            # Search for relevant news using vector search
            try:
                cards = search_news(
                    query=message,
                    top_k=5,
                    min_score=0.5
                )

                # Convert cards to sources format
                sources = [card.to_dict() for card in cards]

                logger.info(f"RAG search found {len(cards)} relevant articles")
            except Exception as e:
                logger.error(f"Error in RAG search: {e}")
                cards = []

        # Get world context and market context
        world_context = None
        market_context = None

        try:
            db = SessionLocal()
            try:
                world_context = get_world_context_for_llm(db)
                market_context = get_market_context_for_llm(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error fetching context: {e}")

        # Build RAG context
        if cards or world_context or market_context:
            rag_context = self._build_rag_context(
                query=message,
                cards=cards,
                world_context=world_context,
                market_context=market_context
            )

        # Build enhanced prompt with RAG context
        if rag_context:
            enhanced_prompt = (
                f"Based on the following context, answer the user's question. "
                f"Cite sources when relevant using [1], [2], etc.\n\n"
                f"{rag_context}\n\n"
                f"User Question: {message}\n\n"
                f"Answer:"
            )
        else:
            enhanced_prompt = message

        # Generate response using ChatWorker
        try:
            chat_worker = get_chat_worker()

            # Convert conversation history if provided
            history = []
            if conversation_history:
                for msg in conversation_history:
                    history.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            result = await chat_worker.generate(args={
                "text": enhanced_prompt,
                "history": history,
                "memory_compact": "",
                "tools_manifest": [],
                "llm_id": None
            })

            answer = result.get("reply", "Je n'ai pas pu générer de réponse.")

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            answer = "Désolé, une erreur s'est produite lors de la génération de la réponse."

        latency_ms = int((time.time() - start_time) * 1000)

        return ChatResponse(
            answer=answer,
            sources=sources,
            cards=cards,
            confidence=confidence if use_rag else 0.5,
            is_rag_response=use_rag and len(cards) > 0,
            latency_ms=latency_ms
        )


# Global service instance
_rag_service: Optional[FedAgentRagService] = None


def get_fedagent_rag_service() -> FedAgentRagService:
    """Get or create the global FedAgent RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = FedAgentRagService()
    return _rag_service
