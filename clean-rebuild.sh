#!/bin/bash

################################################################################
# Script de Nettoyage et Rebuild Complet - FedEdge
#
# Ce script nettoie complètement toutes les images et conteneurs Docker
# et rebuild l'image from scratch
#
# Usage:
#   ./clean-rebuild.sh              # Build et lancer
#   ./clean-rebuild.sh --no-run     # Build seulement (ne pas lancer)
################################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Parse arguments
RUN_AFTER_BUILD=true
if [ "$1" = "--no-run" ]; then
    RUN_AFTER_BUILD=false
fi

# ============================================================================
# 1. Arrêter tous les conteneurs fededge
# ============================================================================

print_header "1/6 : Arrêt des conteneurs"

CONTAINERS=$(docker ps -a --filter "name=fededge" --format "{{.Names}}" 2>/dev/null || true)
if [ -n "$CONTAINERS" ]; then
    echo "$CONTAINERS" | while read container; do
        if [ -n "$container" ]; then
            print_info "Arrêt de $container..."
            docker stop "$container" 2>/dev/null || true
            print_success "Conteneur $container arrêté"
        fi
    done
else
    print_info "Aucun conteneur fededge en cours d'exécution"
fi

# ============================================================================
# 2. Supprimer tous les conteneurs fededge
# ============================================================================

print_header "2/6 : Suppression des conteneurs"

if [ -n "$CONTAINERS" ]; then
    echo "$CONTAINERS" | while read container; do
        if [ -n "$container" ]; then
            print_info "Suppression de $container..."
            docker rm "$container" 2>/dev/null || true
            print_success "Conteneur $container supprimé"
        fi
    done
else
    print_info "Aucun conteneur fededge à supprimer"
fi

# ============================================================================
# 3. Supprimer toutes les images fededge
# ============================================================================

print_header "3/6 : Suppression des images"

IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "fededge|fedgesrv" || true)
if [ -n "$IMAGES" ]; then
    echo "$IMAGES" | while read image; do
        if [ -n "$image" ]; then
            print_info "Suppression de $image..."
            docker rmi "$image" -f 2>/dev/null || true
            print_success "Image $image supprimée"
        fi
    done
else
    print_info "Aucune image fededge à supprimer"
fi

# ============================================================================
# 4. Nettoyer le cache Docker
# ============================================================================

print_header "4/6 : Nettoyage du cache Docker"

print_info "Nettoyage du cache buildx..."
docker builder prune -af > /dev/null 2>&1 || true
print_success "Cache nettoyé"

# ============================================================================
# 5. Rebuild l'image from scratch
# ============================================================================

print_header "5/6 : Rebuild de l'image (sans cache)"

print_info "Construction de l'image fededge:latest..."
print_info "Cela peut prendre plusieurs minutes (compilation de llama.cpp)..."

if docker build --no-cache -f Dockerfile.cpu-full -t fededge:latest .; then
    print_success "Image fededge:latest construite avec succès"

    # Afficher la taille de l'image
    SIZE=$(docker images fededge:latest --format "{{.Size}}")
    print_info "Taille de l'image: $SIZE"
else
    print_error "Échec de la construction de l'image"
    exit 1
fi

# ============================================================================
# 6. Lancer le conteneur (optionnel)
# ============================================================================

if [ "$RUN_AFTER_BUILD" = true ]; then
    print_header "6/6 : Lancement du conteneur"

    # Vérifier que le répertoire data existe
    if [ ! -d "./data" ]; then
        print_info "Création du répertoire ./data"
        mkdir -p ./data
    fi

    print_info "Démarrage du conteneur fededge..."
    docker run -d \
        --name fededge \
        -p 8000:8000 \
        -p 9001:9001 \
        -p 9002:9002 \
        -v "$(pwd)/data:/app/data" \
        fededge:latest

    print_success "Conteneur démarré avec succès"

    # Attendre quelques secondes pour que le serveur démarre
    print_info "Attente du démarrage du serveur (10s)..."
    sleep 10

    # Tester l'API
    print_info "Test de l'API..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "API accessible sur http://localhost:8000"
    else
        print_error "L'API ne répond pas encore, vérifiez les logs:"
        echo "  docker logs -f fededge"
    fi

    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image a été reconstruite et le conteneur est démarré !"
    echo ""
    echo "📊 Informations :"
    echo "  - Conteneur : fededge"
    echo "  - API       : http://localhost:8000"
    echo "  - Chat      : http://localhost:9001"
    echo "  - Embeddings: http://localhost:9002"
    echo ""
    echo "📝 Commandes utiles :"
    echo "  - Voir les logs    : docker logs -f fededge"
    echo "  - Arrêter          : docker stop fededge"
    echo "  - Redémarrer       : docker restart fededge"
    echo "  - Supprimer        : docker stop fededge && docker rm fededge"
    echo ""
else
    print_header "6/6 : Lancement ignoré (--no-run)"

    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image a été reconstruite avec succès !"
    echo ""
    echo "📝 Pour lancer le conteneur :"
    echo "  docker run -d --name fededge -p 8000:8000 -p 9001:9001 -p 9002:9002 -v \$(pwd)/data:/app/data fededge:latest"
    echo ""
fi
