# fededge v0.1.0
# Imed Magroune 09-11-2025
# imed@fededge.net

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Boolean,
    Enum,
    UniqueConstraint,
    Index,
    DECIMAL,
    event,
    BLOB,           # 👈 pour stocker les embeddings binaires
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import datetime
import enum
import sqlite3

# Base de données unifiée - stockée dans /app/data/ (volume persistant)
try:
    from backend.config.paths import DATABASE_URL
except ImportError:
    # Fallback for when imported from different contexts
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from config.paths import DATABASE_URL

Base = declarative_base()

# ==================== ENUMS ====================

class OrderType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    
class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    
class DecisionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REBALANCE = "REBALANCE"

class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

# ==================== TRADING SYSTEM (nouveau) ====================

# Assets table - Liste des cryptomonnaies supportées
class Asset(Base):
    __tablename__ = "asset"
    
    id = Column(String, primary_key=True)  # coingecko ID comme clé primaire
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False, index=True)
    coingecko_id = Column(String, nullable=False, unique=True)
    binance_symbol = Column(String)  # Symbole pour Binance API
    logo_url = Column(String)  # URL du logo
    description = Column(Text)  # Description de l'asset
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    wallet_holdings = relationship("WalletHolding", back_populates="asset")
    wallet_transactions = relationship("WalletTransaction", back_populates="asset")
    
    # Indexes for fast searches
    __table_args__ = (
        Index('idx_asset_symbol', 'symbol'),
        Index('idx_asset_name', 'name'),
    )

# Wallet table - User wallets/wallets
class Wallet(Base):
    __tablename__ = "wallet"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)  # FK to users table if multi-user (future)
    name = Column(String, nullable=False)  # e.g., 'Mon portefeuille principal'
    initial_budget_usd = Column(DECIMAL(20, 8), default=0)  # Budget initial défini par l'utilisateur
    total_value_usd = Column(DECIMAL(20, 8))  # Updated periodically via API prices
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    holdings = relationship("WalletHolding", back_populates="wallet", cascade="all, delete-orphan")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="wallet", cascade="all, delete-orphan")
    decisions = relationship("TradingDecision", back_populates="wallet", cascade="all, delete-orphan")

# Wallet Holdings table - Current asset holdings in wallets
class WalletHolding(Base):
    __tablename__ = "wallet_holding"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(Integer, ForeignKey("wallet.id"), nullable=False)
    asset_id = Column(String, ForeignKey("asset.id"), nullable=False)
    quantity = Column(DECIMAL(20, 8), nullable=False, default=0)
    average_buy_price = Column(DECIMAL(20, 8))  # Average buy price in USD
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="holdings")
    asset = relationship("Asset", back_populates="wallet_holdings")
    
    # Foreign key constraints and unique constraint
    __table_args__ = (
        UniqueConstraint('wallet_id', 'asset_id', name='_wallet_asset_uc'),
        Index('idx_wallet_holding_wallet_id', 'wallet_id'),
        Index('idx_wallet_holding_asset_id', 'asset_id'),
    )

# Wallet Transactions table - Transaction history
# États contextuels
class WorldState(Base):
    __tablename__ = "world_states"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    summary = Column(Text, nullable=False)
    sentiment_score = Column(Float)  # -1 à 1 pour mesurer le sentiment global
    key_events = Column(JSON)  # Liste des événements majeurs
    raw_data = Column(Text)
    source = Column(String)  # Source des données (API, scraping, etc.)
    
    # Relations
    decisions = relationship("TradingDecision", back_populates="world_state")

class MarketState(Base):
    __tablename__ = "market_states"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    total_market_cap = Column(Float)
    btc_dominance = Column(Float)
    fear_greed_index = Column(Integer)  # 0-100
    top_gainers = Column(JSON)
    top_losers = Column(JSON)
    trending_coins = Column(JSON)
    raw_data = Column(Text)
    source = Column(String)
    
    # Relations
    decisions = relationship("TradingDecision", back_populates="market_state")

class AssetState(Base):
    __tablename__ = "asset_states"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    ticker = Column(String, nullable=False, index=True)
    price = Column(Float)
    volume_24h = Column(Float)
    price_change_24h = Column(Float)
    market_cap = Column(Float)
    summary = Column(Text, nullable=False)
    sentiment_score = Column(Float)  # -1 à 1
    technical_indicators = Column(JSON)  # RSI, MACD, etc.
    raw_data = Column(Text)
    source = Column(String)
    
    # Relations
    decisions = relationship("TradingDecision", back_populates="asset_state")
    
    # Index pour requêtes fréquentes
    __table_args__ = (
        Index('idx_asset_ticker_timestamp', 'ticker', 'timestamp'),
    )

# ==================== SYSTÈME TRANSACTIONS (basé sur wallets) ====================

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey("wallet.id"), nullable=False)
    decision_id = Column(Integer, ForeignKey("trading_decisions.id"))
    asset_id = Column(String, ForeignKey("asset.id"), nullable=False, index=True)  # coingecko_id
    type = Column(Enum(TransactionType), nullable=False)  # BUY or SELL
    amount = Column(DECIMAL(20, 8), nullable=False)  # Quantité d'asset
    price_at_time = Column(DECIMAL(20, 8), nullable=False)  # Prix au moment de la transaction
    total_value = Column(DECIMAL(20, 8), nullable=False)  # amount * price
    fees = Column(DECIMAL(20, 8), default=0)
    tx_hash = Column(String)  # optionnel si tu veux tracer on-chain/CEX
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Données contextuelles
    world_context = Column(Text)
    market_context = Column(Text)
    asset_context = Column(Text)
    reasoning = Column(Text)
    
    # Relations
    wallet = relationship("Wallet", back_populates="transactions")
    asset = relationship("Asset", back_populates="wallet_transactions")
    decision = relationship("TradingDecision", back_populates="transactions")
    
    # Index pour requêtes fréquentes
    __table_args__ = (
        Index('idx_wallet_transaction_timestamp', 'wallet_id', 'timestamp'),
        Index('idx_wallet_transaction_asset', 'asset_id', 'timestamp'),
    )
# ==================== SYSTÈME DE DÉCISION ====================

class TradingDecision(Base):
    __tablename__ = "trading_decisions"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Contexte de la décision
    wallet_id = Column(Integer, ForeignKey("wallet.id"))
    world_state_id = Column(Integer, ForeignKey("world_states.id"))
    market_state_id = Column(Integer, ForeignKey("market_states.id"))
    asset_state_id = Column(Integer, ForeignKey("asset_states.id"))
    
    # Décision prise
    ticker = Column(String, nullable=False, index=True)
    decision_type = Column(Enum(DecisionType), nullable=False)
    quantity = Column(Float)
    target_price = Column(Float)
    confidence_score = Column(Float)  # 0.0 à 1.0
    reasoning = Column(Text, nullable=False)
    
    # Métadonnées
    decision_data = Column(JSON)  # Données structurées complètes
    execution_status = Column(String, default="PENDING")
    agent_version = Column(String)  # Version de l'agent qui a pris la décision
    processing_time_ms = Column(Integer)  # Temps de traitement en ms
    performance_score = Column(Float)  # Score de performance pour RL
    
    # Relations
    wallet = relationship("Wallet", back_populates="decisions")
    world_state = relationship("WorldState", back_populates="decisions")
    market_state = relationship("MarketState", back_populates="decisions")
    asset_state = relationship("AssetState", back_populates="decisions")
    transactions = relationship("WalletTransaction", back_populates="decision")

# Snapshots pour historique et analyse
class TradingEnvironment(Base):
    __tablename__ = "trading_environments"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, default="Default Environment")
    initial_budget = Column(Float, default=10000.0)
    current_budget = Column(Float, default=10000.0)
    objective = Column(Text, default="Maximiser le profit avec une stratégie équilibrée.")

# ==================== NEWS SYSTEM ====================

class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    url = Column(String, unique=True)
    source = Column(String)
    author = Column(String)  # Champ manquant ajouté
    published_at = Column(DateTime)
    sentiment_score = Column(Float)  # -1 à 1
    relevance_score = Column(Float)  # 0 à 1
    crypto_mentions = Column(JSON)  # Liste des cryptos mentionnées
    is_processed = Column(Boolean, default=False)  # Indique si l'article a été traité par le WorldContextAgent
    is_active = Column(Boolean, default=True)  # Indique si l'article est actif
    scraped_date = Column(DateTime, default=datetime.datetime.utcnow)  # Date de scraping
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 💡 champs manquants utilisés dans crud.py
    summary = Column(Text)                         # résumé généré par l’IA
    keywords = Column(JSON)                        # liste JSON
    mentioned_assets = Column(JSON)                # liste JSON
    category = Column(String)                      # "market", "regulation", etc.

    embedding_generated = Column(Boolean, default=False)  # pour RAG
    embedding_model = Column(String)
    embedding_date = Column(DateTime)
    
    __table_args__ = (
        Index('idx_news_published_at', 'published_at'),
        Index('idx_news_source', 'source'),
    )

# ==================== RAG SYSTEM ====================
# ==================== RAG SYSTEM (NOUVEAU) ====================

class RagDocument(Base):
    """
    Document RAG générique (PDF, texte, URL, news, etc.)
    - title / url / domain décrivent la source
    - file_path permet de retrouver le fichier sur disque (PDF téléchargé)
    """
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True)
    domain = Column(String, index=True)            # ex: "defi", "btc", "regulation", "user"
    file_path = Column(String)                     # chemin local vers le PDF/fichier
    downloaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relation vers les chunks
    chunks = relationship(
        "RagChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RagChunk(Base):
    """
    Chunk de texte indexé pour le RAG:
    - content: texte
    - embedding: vecteur float32 sérialisé en BLOB
    - domain: rappel du domaine pour filtrage rapide
    """
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("rag_documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(BLOB)                       # vecteur numpy.float32.tobytes()
    page_number = Column(Integer, nullable=True)   # optionnel si PDF
    chunk_index = Column(Integer)                  # ordre du chunk dans le doc
    domain = Column(String, index=True)

    document = relationship("RagDocument", back_populates="chunks")

    __table_args__ = (
        Index("idx_rag_chunk_domain", "domain"),
        Index("idx_rag_chunk_doc", "doc_id"),
    )


class RagTrace(Base):
    """
    Traces des requêtes RAG (pour debug/metrics):
    - chunk_ids: liste des chunks utilisés
    - sources: métadonnées sur les sources (titre, url, chunk index)
    """
    __tablename__ = "rag_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    question = Column(Text, nullable=False)
    chunk_ids = Column(JSON)                       # liste d'IDs de RagChunk
    model = Column(String)                         # modèle utilisé pour répondre
    latency_ms = Column(Integer)                   # latence totale
    answer_preview = Column(Text)                  # premiers caractères
    full_answer = Column(Text)                     # réponse complète
    sources = Column(JSON)                         # [{"title":..., "url":..., "chunk":...}, ...]

    __table_args__ = (
        Index("idx_rag_trace_timestamp", "timestamp"),
    )



# ==================== MÉTRIQUES ====================

class TradingMetrics(Base):
    __tablename__ = "trading_metrics"
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey("wallet.id"), unique=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Métriques de performance
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float)
    average_win = Column(Float)
    average_loss = Column(Float)
    profit_factor = Column(Float)
    
    # Métriques de risque
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    volatility = Column(Float)
    
    # Métriques par asset
    best_performing_asset = Column(String)
    worst_performing_asset = Column(String)
    most_traded_asset = Column(String)

# ==================== SIMULATIONS ====================

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Configuration
    wallet_id = Column(Integer, ForeignKey("wallet.id"), nullable=False)
    strategy = Column(String, nullable=False)  # Stratégie utilisateur (prudent, balanced, aggressive)
    frequency_minutes = Column(Integer, nullable=False)  # Fréquence en minutes
    
    # État
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)  # Indique si la simulation est actuellement en cours
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_run_at = Column(DateTime)  # Dernière exécution
    next_run_at = Column(DateTime)  # Prochaine exécution planifiée
    
    # Statistiques
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    last_error = Column(Text)  # Dernière erreur rencontrée
    
    # Relations
    wallet = relationship("Wallet", back_populates="simulations")
    
    __table_args__ = (
        Index('idx_simulations_active', 'is_active'),
        Index('idx_simulations_next_run', 'next_run_at'),
        UniqueConstraint('name', name='uq_simulation_name'),
    )



# ==================== COPILOT / FEDEDGE CORE ====================


class CopilotConsciousSnapshot(Base):
    __tablename__ = "copilot_conscious_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    context_json = Column(JSON, nullable=False)         # état de conscience complet
    vital_signals_json = Column(JSON)                   # signaux vitaux (liste ou dict)
    summary_text = Column(Text)                         # résumé humain optionnel
    source_event_id = Column(String)                    # lien vers CopilotEvent.id

class CopilotAgent(Base):
    """
    Décrit un agent FedEdge logique (core, teacher, risk_guard, etc.)
    """
    __tablename__ = "copilot_agents"

    id = Column(String, primary_key=True)          # "fededge_core", "fededge_teacher", ...
    name = Column(String, nullable=False)          # "FedEdge core copilot"
    role = Column(String, nullable=False)          # "core_copilot", "teacher", ...
    mission = Column(Text, nullable=False)         # description longue
    profile_json = Column(JSON, nullable=False)    # whoami, tools, style, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class CopilotMission(Base):
    """
    Missions de l'agent (daily_news_digest, paper_trade_monitor, teacher_update, ...)
    """
    __tablename__ = "copilot_missions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("copilot_agents.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    kind = Column(String, nullable=False)          # "periodic" | "event_driven" | "adhoc"
    status = Column(String, nullable=False, default="active")  # "active" | "paused"
    priority = Column(Integer, nullable=False, default=5)      # 1=high, 10=low
    schedule_cron = Column(String)                 # si périodique
    last_run_ts = Column(DateTime)
    next_run_ts = Column(DateTime)
    config = Column(JSON)                          # paramètres supplémentaires
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    agent = relationship("CopilotAgent")


class CopilotStateKV(Base):
    """
    KV store pour l'état compact du monde/système vu par FedEdge :
    - market_overview
    - wallets_summary
    - sim_overview
    - news_digest_today_YYYY-MM-DD
    - user_profile
    - teacher_stats
    etc.
    """
    __tablename__ = "copilot_state_kv"

    key = Column(String, primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class CopilotEvent(Base):
    """
    Log d'événements logiques pour FedEdge (en plus des events en mémoire) :
    - topic: "user", "news", "wallet", "sim", "rag", "teacher"
    - type: "USER_MESSAGE", "NEWS_INGESTED", etc.
    """
    __tablename__ = "copilot_events"

    id = Column(String, primary_key=True)          # peut reprendre Event.id (e_...)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    topic = Column(String, nullable=False)
    type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)         # snapshot JSON de l'event métier


class TeachingExample(Base):
    """
    Dataset pour entraîner/finetuner un petit modèle (teacher mode) :
    - input_text / target_text : Q/R idéales
    """
    __tablename__ = "teaching_examples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String, nullable=False)   # "news", "trade", "user_note", "doc"
    source_id = Column(String)                     # id de NewsArticle, TradingDecision, RagDocument, ...
    level = Column(String)                         # "beginner", "intermediate", "advanced"
    input_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=False)
    tags_json = Column(JSON)                       # ["risk","btc","trend"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    used_for_train = Column(Boolean, default=False)
    metadata_json = Column(JSON)                   # {"reason": "...", "model_hint": "..."}


class UserFact(Base):
    """
    Faits structurés sur l'utilisateur (profil de risque, préférences, horizon, etc.)
    """
    __tablename__ = "user_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)      # ou TEXT si besoin
    key = Column(String, nullable=False)           # "risk_profile", "favorite_pairs", ...
    value_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_fact_key"),
    )


class UserNote(Base):
    """
    Notes importantes exprimées par l'utilisateur (à garder en mémoire longue)
    """
    __tablename__ = "user_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    source_event_id = Column(String)               # id de CopilotEvent du chat
    note_text = Column(Text, nullable=False)
    tags_json = Column(JSON)                       # ["important","risk","pref"]
    is_pinned = Column(Boolean, default=False)     # note épinglée

    wallet_id = Column(Integer, ForeignKey("wallet.id"))  # optionnel: lien vers wallet
    ticker = Column(String)                                 # optionnel: lien vers un asset



#########################################################################################################


# ==================== AGENT CORE (générique) ====================

class AgentConfig(Base):
    """
    Config générique d'un agent :
    - whoami, mission, tools, schema de conscience...
    """
    __tablename__ = "agent_config"

    id = Column(String, primary_key=True)     # ex: "core_agent", "risk_guard"
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)     # "copilot", "teacher", "monitor", ...
    profile_json = Column(JSON, nullable=False)  # dict: whoami, mission, tools, conscious_slots, etc.

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class AgentMemoryKV(Base):
    """
    KV store générique pour la mémoire d'un agent.
    scopes possibles: "facts", "working", "meta", "long_term", ...
    """
    __tablename__ = "agent_memory_kv"

    agent_id = Column(String, ForeignKey("agent_config.id"), primary_key=True)
    scope = Column(String, primary_key=True)       # ex: "facts" | "working" | "meta"
    key = Column(String, primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    agent = relationship("AgentConfig")


class AgentEvent(Base):
    """
    Log d'événements génériques pour l'agent core.
    (équivalent générique de CopilotEvent)
    """
    __tablename__ = "agent_events"

    id = Column(String, primary_key=True)  # "e_<timestamp>_..." ou autre
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False)

    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    topic = Column(String, nullable=False)         # "user", "external", "tool", "timer", "trace", ...
    type = Column(String, nullable=False)          # "USER_MESSAGE", "TIMER_TICK", "TOOL_RESULT", ...
    source = Column(String, nullable=False)        # "frontend", "scheduler", "tool:get_market", ...
    payload_json = Column(JSON, nullable=False)    # contenu métier

    agent = relationship("AgentConfig")


class AgentSnapshot(Base):
    """
    Snapshots de l'état conscient / mémoire globale de l'agent.
    Optionnel, pratique pour debug, UI, analytics.
    """
    __tablename__ = "agent_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False, index=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    snapshot_json = Column(JSON, nullable=False)   # dump de MemorySnapshot + conscious.context
    summary_text = Column(Text)                    # résumé humain optionnel
    source_event_id = Column(String)               # lien vers AgentEvent.id

    agent = relationship("AgentConfig")


# ==================== ENTITY GRAPH (Phase 2.5) ====================

class AgentEntityNode(Base):
    """
    Entity nodes for Entity-Relationship Memory Graph

    Stores entities: users, assets, patterns, signals, decisions, outcomes, etc.
    """
    __tablename__ = "agent_entity_nodes"

    id = Column(String, primary_key=True)  # Entity ID (e.g., "ent_abc123", "user_default")
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False, index=True)

    # Entity properties
    type = Column(String, nullable=False, index=True)  # "user", "asset", "pattern", etc.
    label = Column(String, nullable=False)  # Display label

    # Flexible attributes (JSON)
    attributes = Column(JSON, nullable=False)  # Entity-specific attributes

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    tags = Column(JSON)  # List of tags

    # Importance and consolidation scores
    importance = Column(Float, default=0.5)  # 0..1
    consolidation = Column(Float, default=0.0)  # Accumulates with usage

    # Relationships
    agent = relationship("AgentConfig")

    # Indexes for performance
    __table_args__ = (
        Index('idx_agent_entity_type', 'agent_id', 'type'),
        Index('idx_agent_entity_created', 'agent_id', 'created_at'),
    )


class AgentEntityRelation(Base):
    """
    Relations between entities in the Entity Graph

    Stores relations: OWNS, WATCHES, FOLLOWS, DECIDED, RESULTED_IN, etc.
    """
    __tablename__ = "agent_entity_relations"

    id = Column(String, primary_key=True)  # Relation ID (e.g., "rel_xyz789")
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False, index=True)

    # Relation endpoints
    source_id = Column(String, ForeignKey("agent_entity_nodes.id"), nullable=False, index=True)
    target_id = Column(String, ForeignKey("agent_entity_nodes.id"), nullable=False, index=True)

    # Relation properties
    type = Column(String, nullable=False, index=True)  # "OWNS", "WATCHES", etc.

    # Flexible attributes (JSON)
    attributes = Column(JSON, nullable=False)  # Relation-specific attributes

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Strength/confidence
    strength = Column(Float, default=0.7)  # 0..1

    # Relationships
    agent = relationship("AgentConfig")
    source = relationship("AgentEntityNode", foreign_keys=[source_id])
    target = relationship("AgentEntityNode", foreign_keys=[target_id])

    # Indexes for performance
    __table_args__ = (
        Index('idx_agent_relation_source', 'agent_id', 'source_id'),
        Index('idx_agent_relation_target', 'agent_id', 'target_id'),
        Index('idx_agent_relation_type', 'agent_id', 'type'),
    )


##################################################################################################################

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    """Créer toutes les tables dans la base de données"""
    Base.metadata.create_all(bind=engine)
    
    # Create view for RAG queries (Qdrant handles vectors separately)
    _create_rag_view()

def _create_rag_view():
    """Create view for RAG queries - vectors stored in Qdrant"""
    try:
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Create view for RAG queries
            conn.execute(text(
                "CREATE VIEW IF NOT EXISTS news_rag_view AS "
                "SELECT id, title, url, source, published_at, summary, content "
                "FROM news_articles "
                "WHERE is_active = 1"
            ))
            
            conn.commit()
            print("✅ RAG view created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not create RAG view: {e}")

def get_db():
    """Générateur de session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()