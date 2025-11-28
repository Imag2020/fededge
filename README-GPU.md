# Guide d'utilisation GPU pour FedEdge

## 🎯 Image actuelle : CPU/BLAS optimisé (générique)

L'image `imedmag2020/fededge:latest` est **100% générique** et fonctionne sur :
- ✅ CPU uniquement (Intel, AMD, ARM)
- ✅ Serveurs sans GPU
- ✅ Machines avec GPU NVIDIA (mais utilise CPU/BLAS)

### Performance CPU/BLAS

Pour les modèles 1B-4B :
- **Throughput** : 10-30 tokens/s (selon CPU)
- **Latence** : Acceptable pour la plupart des cas
- **Avantage** : Pas de dépendance GPU, fonctionne partout

---

## 🚀 Option 1 : Utiliser l'image CPU (Recommandé)

```bash
# Sur n'importe quelle machine
docker pull imedmag2020/fededge:v0.1.0

docker run -d --name fededge \
  -p 8000:8000 -p 9001:9001 -p 9002:9002 \
  -v $(pwd)/data:/app/data \
  imedmag2020/fededge:v0.1.0
```

**Avantages** :
- ✅ Fonctionne immédiatement
- ✅ Pas de configuration GPU requise
- ✅ Portable entre machines
- ✅ Performance acceptable pour modèles légers

---

## ⚡ Option 2 : Activer CUDA (pour vraies performances GPU)

Si vous avez une **NVIDIA GPU** et voulez de vraies performances GPU :

### Étape 1 : Compiler llama-server avec CUDA localement

```bash
# Sur votre machine avec NVIDIA GPU
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Compiler avec CUDA
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc)

# Le binaire est dans build/bin/llama-server
# Copier dans votre projet
cp build/bin/llama-server ~/fededge/bin-gpu/llama-server
```

### Étape 2 : Lancer avec le binaire CUDA

```bash
cd ~/fededge

# Lancer l'image en montant le binaire CUDA
docker run -d --gpus all --name fededge-gpu \
  -v $(pwd)/bin-gpu/llama-server:/app/bin/llama-server:ro \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 -p 9001:9001 -p 9002:9002 \
  imedmag2020/fededge:v0.1.0
```

### Étape 3 : Vérifier que CUDA est utilisé

```bash
# Vérifier les logs
docker logs fededge-gpu | grep -i gpu

# Devrait afficher :
# 🎮 GPU NVIDIA détecté, activation GPU (toutes couches)
# 🚀 lancement chat: ... -ngl 99 ...
```

**Performance attendue avec CUDA** :
- **Throughput** : 100-500 tokens/s (selon GPU)
- **Latence** : 5-10x plus rapide que CPU
- **Limitation** : Nécessite compilation locale du binaire

---

## 📊 Comparaison

| Méthode | Setup | Portabilité | Performance | Complexité |
|---------|-------|-------------|-------------|------------|
| **Image CPU** | ✅ Pull & run | ✅✅✅ Partout | ⚡ 10-30 tok/s | ✅ Simple |
| **Image CPU + binaire CUDA** | ⚠️ Compile local | ⚠️ Spécifique GPU | ⚡⚡⚡ 100-500 tok/s | ⚠️ Moyen |

---

## 🎯 Recommandation

### Pour développement / test :
→ **Image CPU** (`imedmag2020/fededge:latest`)

### Pour production avec GPU :
→ **Image CPU + binaire CUDA monté** (Option 2)

### Pourquoi cette approche ?

1. ✅ **Image générique** : Fonctionne partout
2. ✅ **Pas de build compliqué** : Image CPU build facilement
3. ✅ **GPU optionnel** : Ajoutez le binaire CUDA si besoin
4. ✅ **Flexible** : Même image pour CPU et GPU

---

## 🔧 Alternative : Builder une image GPU dédiée

Si vous voulez une image GPU dédiée pré-compilée, il faut :

1. Builder sur une **machine avec NVIDIA GPU** (pas en émulation)
2. Ou utiliser un service CI/CD avec GPU (GitHub Actions GPU, GitLab CI)
3. Ou accepter que l'image ne soit pas multi-plateforme

**Dockerfile simplifié pour build local GPU** :

```dockerfile
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04 AS build
RUN apt-get update && apt-get install -y git cmake build-essential
WORKDIR /opt
RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /opt/llama.cpp
RUN cmake -B build -DGGML_CUDA=ON && cmake --build build -j$(nproc)

FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04
# ... copier build/bin/llama-server et setup Python ...
```

Mais cette image devra être **buildée localement** avec un vrai GPU, pas via Docker buildx.

---

## ❓ Questions fréquentes

**Q: L'image CPU détecte-t-elle le GPU ?**
R: Oui, `start_llamacpp.sh` détecte automatiquement, mais sans binaire CUDA, il utilise CPU/BLAS.

**Q: Puis-je utiliser l'image CPU en production ?**
R: Oui ! Pour des modèles 1B-4B, CPU/BLAS est souvent suffisant.

**Q: Combien gagne-t-on avec CUDA ?**
R: 5-10x plus rapide selon le GPU (RTX 3090 : ~300 tok/s vs CPU : ~30 tok/s).

**Q: Pourquoi pas d'image GPU multi-plateforme ?**
R: La compilation CUDA dans Docker buildx (émulation) est très instable. Il faut un vrai GPU pour compiler.
