# Système RAG - Documentation

## 📚 Vue d'ensemble

Le système RAG (Retrieval-Augmented Generation) permet d'ingérer des documents (PDFs, URLs) et de les interroger via une recherche hybride combinant :
- **Similarité sémantique** (embeddings vectoriels)
- **Recherche lexicale** (BM25)

## 🗄️ Architecture

### Tables SQL

```sql
rag_documents
├── id (PK)
├── title
├── url (unique)
├── domain (index)
├── file_path
└── downloaded_at

rag_chunks
├── id (PK)
├── doc_id (FK → rag_documents)
├── content (TEXT)
├── embedding (BLOB)  ✅ Stockage binaire optimisé
├── page_number
├── chunk_index
└── domain (index)

rag_traces
├── id (PK)
├── timestamp
├── question
├── chunk_ids (JSON)
├── model
├── latency_ms
├── answer_preview
├── full_answer
└── sources (JSON)
```

## 🔧 Fonctions utilitaires

### `rag_helpers.py`

#### Conversion vecteurs
```python
from backend.utils.rag_helpers import vector_to_blob, blob_to_vector

# Numpy → BLOB
blob = vector_to_blob(my_vector)

# BLOB → Numpy
vector = blob_to_vector(blob)
```

#### Chunking
```python
from backend.utils.rag_helpers import chunk_text

chunks = chunk_text(long_text, chunk_size=300, overlap=50)
# Retourne: ['chunk1...', 'chunk2...', ...]
```

#### Ingestion PDF
```python
from backend.utils.rag_helpers import ingest_pdf

success = ingest_pdf(
    pdf_path="data/docs/bitcoin.pdf",
    url="https://bitcoin.org/bitcoin.pdf",
    domain="crypto",
    title="Bitcoin Whitepaper"
)
```

#### Recherche hybride
```python
from backend.utils.rag_helpers import hybrid_search

results = hybrid_search(
    query="What is Bitcoin?",
    domain="crypto",  # Optionnel
    top_k=5
)

for chunk, score in results:
    print(f"Score: {score:.4f}")
    print(f"Content: {chunk.content[:200]}...")
```

#### Statistiques
```python
from backend.utils.rag_helpers import get_stats

stats = get_stats()
print(f"Documents: {stats['total_documents']}")
print(f"Chunks: {stats['total_chunks']}")
print(f"Domaines: {stats['domains']}")
```

## 🧪 Tests

### Script de test interactif

```bash
cd /local/home/im267926/feddev
python backend/scripts/test_rag.py
```

Menu :
1. Tester l'ingestion d'un PDF
2. Tester la recherche
3. Afficher les statistiques
4. Quitter

### Exemple Python

```python
from backend.utils.rag_helpers import ingest_pdf, hybrid_search, build_bm25_index

# 1. Ingérer un document
ingest_pdf(
    pdf_path="data/docs/ethereum.pdf",
    url="https://ethereum.org/whitepaper.pdf",
    domain="crypto",
    title="Ethereum Whitepaper"
)

# 2. Construire l'index BM25
build_bm25_index()

# 3. Rechercher
results = hybrid_search("smart contracts", domain="crypto", top_k=3)

for chunk, score in results:
    print(f"\n✅ Score: {score:.4f}")
    print(f"📄 {chunk.content[:300]}...\n")
```

## 📦 Dépendances requises

```bash
pip install numpy
pip install rank-bm25
pip install PyPDF2
```

Vérification :
```python
import numpy as np
from rank_bm25 import BM25Okapi
from PyPDF2 import PdfReader
```

## 🔄 Workflow complet

### 1. Préparer les documents

```bash
mkdir -p data/docs
# Copier vos PDFs dans data/docs/
```

### 2. Ingérer les documents

```python
from backend.utils.rag_helpers import ingest_pdf

docs = [
    ("data/docs/bitcoin.pdf", "https://bitcoin.org/bitcoin.pdf", "Bitcoin Whitepaper"),
    ("data/docs/ethereum.pdf", "https://ethereum.org/whitepaper.pdf", "Ethereum Whitepaper"),
]

for pdf_path, url, title in docs:
    ingest_pdf(pdf_path, url, "crypto", title)
```

### 3. Construire l'index

```python
from backend.utils.rag_helpers import build_bm25_index

build_bm25_index()
```

### 4. Interroger

```python
from backend.utils.rag_helpers import hybrid_search

results = hybrid_search("proof of work vs proof of stake", domain="crypto")

for chunk, score in results[:3]:
    print(f"Score: {score:.4f}")
    print(chunk.content)
    print("-" * 80)
```

## ⚙️ Configuration

### Paramètres de chunking

Dans `rag_helpers.py` :

```python
CHUNK_SIZE = 300  # Nombre de mots par chunk
OVERLAP = 50      # Overlap entre chunks
```

### Poids de recherche hybride

Dans `hybrid_search()` :

```python
final_score = 0.7 * e_score + 0.3 * (b_score / 10)
#             ^^^              ^^^
#          Embedding          BM25
```

Ajuster selon vos besoins :
- Plus de poids sur embedding → recherche sémantique
- Plus de poids sur BM25 → recherche lexicale

## 🚀 Intégration dans le chat

### Exemple d'utilisation dans le chat

```python
from backend.utils.rag_helpers import hybrid_search

def handle_user_question(question: str) -> str:
    # Rechercher les chunks pertinents
    results = hybrid_search(question, domain="crypto", top_k=3)

    if not results:
        return "Désolé, je n'ai pas trouvé d'information pertinente."

    # Construire le contexte
    context = "\n\n".join([chunk.content for chunk, _ in results])

    # Générer la réponse avec le LLM
    prompt = f"""
    Context from knowledge base:
    {context}

    User question: {question}

    Answer based on the context above:
    """

    # Appeler le LLM avec le prompt...
    return llm_response
```

## 🔍 Debugging

### Vérifier les embeddings

```python
from backend.utils.rag_helpers import blob_to_vector
from backend.db.models import RagChunk, SessionLocal

session = SessionLocal()
chunk = session.query(RagChunk).first()

if chunk:
    vec = blob_to_vector(chunk.embedding)
    print(f"Dimension: {vec.shape}")  # (384,) par défaut
    print(f"Type: {vec.dtype}")       # float32
    print(f"Min/Max: {vec.min():.4f} / {vec.max():.4f}")
```

### Vérifier l'index BM25

```python
from backend.utils.rag_helpers import bm25_index, get_all_domains

domains = get_all_domains()
for domain in domains:
    index = bm25_index.get(domain)
    if index:
        print(f"✅ {domain}: {len(index.doc_freqs)} documents indexés")
    else:
        print(f"❌ {domain}: pas d'index BM25")
```

## ⚠️ Notes importantes

### Embeddings

Le fichier `rag_helpers.py` utilise le service **LlamaCpp** sur le port 9002 :

✅ **Modèle** : EmbeddingGemma-300M (GGUF Q8)
✅ **Dimension** : 768
✅ **Endpoint** : `http://localhost:9002/v1/embeddings`
✅ **Normalisation** : L2 (vecteurs unitaires)

Le service est accessible via `get_llamacpp_embedder()` depuis `services/llamacpp_embeddings.py`.

### Performance

- Les embeddings sont stockés en **BLOB binaire** (optimisé)
- L'index BM25 est en **mémoire** (rapide mais volatile)
- Reconstruire l'index BM25 après chaque ingestion

### Domaines

Utilisez des domaines cohérents :
- `"crypto"` : cryptomonnaies, blockchain
- `"finance"` : marchés financiers
- `"tech"` : documentation technique
- etc.

## 📊 Monitoring

```python
from backend.utils.rag_helpers import get_stats

stats = get_stats()
print(f"""
📊 RAG System Stats
━━━━━━━━━━━━━━━━━━
Documents: {stats['total_documents']}
Chunks: {stats['total_chunks']}
Domaines: {len(stats['domains'])}

Répartition:
""")

for domain, count in stats['chunks_per_domain'].items():
    print(f"  • {domain}: {count} chunks")
```

## 🎯 Intégration complète

1. ✅ Schéma SQL mis à jour (BLOB pour embeddings)
2. ✅ Helpers créés
3. ✅ Script de test
4. ✅ Intégré avec LlamaCpp embeddings (port 9002)
5. ✅ API REST créée pour le RAG (/api/rag/*)
6. ✅ Intégré dans le chat FedAgent (outil RAG)
7. ✅ Initialisation BM25 au démarrage du backend
8. ⏳ Ajouter l'ingestion d'URLs (crawling)
9. ⏳ Implémenter la déduplication de chunks

## 🌐 API REST Endpoints

### POST /api/rag/search
Recherche hybride dans les documents

**Body:**
```json
{
  "query": "What is Bitcoin?",
  "domain": "crypto",  // optionnel
  "top_k": 5           // optionnel, défaut: 5
}
```

**Response:**
```json
{
  "success": true,
  "query": "What is Bitcoin?",
  "results": [
    {
      "content": "Bitcoin is a decentralized...",
      "score": 0.8512,
      "doc_id": 1,
      "chunk_index": 0,
      "domain": "crypto",
      "page_number": null
    }
  ],
  "count": 5
}
```

### POST /api/rag/ingest
Upload et ingestion d'un PDF

**Form Data:**
- `file`: PDF file (multipart/form-data)
- `url`: URL source (optionnel)
- `domain`: Domaine (défaut: "crypto")
- `title`: Titre (optionnel, utilise le nom du fichier)

**Response:**
```json
{
  "success": true,
  "message": "PDF 'Bitcoin Whitepaper' ingéré avec succès",
  "file_path": "/path/to/bitcoin.pdf",
  "domain": "crypto"
}
```

### GET /api/rag/stats
Statistiques du système RAG

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_documents": 5,
    "total_chunks": 120,
    "domains": ["crypto", "finance"],
    "chunks_per_domain": {
      "crypto": 80,
      "finance": 40
    }
  }
}
```

### GET /api/rag/documents
Liste tous les documents

**Response:**
```json
{
  "success": true,
  "documents": [
    {
      "id": 1,
      "title": "Bitcoin Whitepaper",
      "url": "https://bitcoin.org/bitcoin.pdf",
      "domain": "crypto",
      "file_path": "/path/to/bitcoin.pdf",
      "downloaded_at": "2025-11-01T12:00:00",
      "chunks_count": 14
    }
  ],
  "count": 1
}
```

### DELETE /api/rag/document/{doc_id}
Supprime un document et ses chunks

**Response:**
```json
{
  "success": true,
  "message": "Document 1 supprimé"
}
```

## 💬 Utilisation dans le Chat

Le système RAG est automatiquement disponible dans le chat via l'outil `<tool>rag: query</tool>`.

**Exemples:**
```
User: What is proof of work?
Assistant: <tool>rag: proof of work</tool>
System: [1] (score 0.85): Proof of Work is a consensus mechanism...

User: Tell me about smart contracts
Assistant: <tool>rag: smart contracts</tool>
System: [1] (score 0.82): Smart contracts are self-executing...
```

Le chat utilise hybrid_search (70% embedding + 30% BM25) et fait un fallback vers les articles de news si aucun document RAG n'est trouvé.

---

**Auteur** : FedEdge AI Team
**Dernière mise à jour** : 2025-11-01
