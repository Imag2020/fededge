#!/bin/bash

################################################################################
# Script de Build Multi-Plateforme GPU - FedEdge
#
# Ce script construit et pousse l'image Docker GPU pour amd64 et arm64
# Compatible avec: NVIDIA GPU (amd64), NVIDIA Jetson (arm64)
#
# Usage:
#   export DOCKER_USER=votre_username
#   export VERSION=v1.0.0
#   ./build-multiplatform-gpu.sh              # Build et push
#   ./build-multiplatform-gpu.sh --test       # Build test local sans push
#   ./build-multiplatform-gpu.sh --amd64-only # Build amd64 uniquement
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
TEST_MODE=false
AMD64_ONLY=false
if [ "$1" = "--test" ]; then
    TEST_MODE=true
elif [ "$1" = "--amd64-only" ]; then
    AMD64_ONLY=true
fi

# ============================================================================
# Vérification des variables d'environnement
# ============================================================================

print_header "Vérification de la configuration"

if [ -z "$DOCKER_USER" ] && [ "$TEST_MODE" = false ]; then
    print_error "La variable DOCKER_USER n'est pas définie"
    echo ""
    echo "Définissez-la avec:"
    echo "  export DOCKER_USER=votre_username"
    echo ""
    echo "Ou utilisez le mode test local:"
    echo "  ./build-multiplatform-gpu.sh --test"
    exit 1
fi

if [ -z "$VERSION" ]; then
    VERSION="latest"
    print_info "VERSION non définie, utilisation de 'latest'"
else
    print_success "VERSION: $VERSION"
fi

if [ "$TEST_MODE" = false ]; then
    print_success "DOCKER_USER: $DOCKER_USER"
fi

# ============================================================================
# Vérification de buildx
# ============================================================================

print_header "Vérification de Docker buildx"

if ! docker buildx version > /dev/null 2>&1; then
    print_error "Docker buildx n'est pas installé"
    echo ""
    echo "Installez-le avec:"
    echo "  docker buildx install"
    exit 1
fi

print_success "Docker buildx est disponible"

# Vérifier si le builder existe
if ! docker buildx ls | grep -q "fededge-builder"; then
    print_info "Création du builder multi-plateforme..."
    docker buildx create --name fededge-builder --use
    print_success "Builder créé"
else
    print_info "Utilisation du builder existant: fededge-builder"
    docker buildx use fededge-builder
fi

# Bootstrap du builder si nécessaire
print_info "Vérification du builder..."
docker buildx inspect --bootstrap > /dev/null 2>&1
print_success "Builder prêt"

# ============================================================================
# Construction de l'image
# ============================================================================

if [ "$TEST_MODE" = true ]; then
    print_header "Build test local GPU (sans push)"

    print_info "Construction pour linux/amd64 uniquement..."
    print_info "Cela peut prendre plusieurs minutes..."

    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.gpu \
        --tag fededge:gpu-test \
        --load \
        .

    print_success "Build test GPU réussi !"

    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image de test GPU a été construite avec succès !"
    echo ""
    echo "📊 Image créée : fededge:gpu-test"
    echo ""
    echo "📝 Pour tester (nécessite NVIDIA GPU + nvidia-docker) :"
    echo "  docker run -d --gpus all --name fededge-gpu-test \\"
    echo "    -p 8000:8000 -p 9001:9001 -p 9002:9002 \\"
    echo "    -v \$(pwd)/data:/app/data \\"
    echo "    fededge:gpu-test"
    echo ""
    echo "Pour le build multi-plateforme complet, relancez sans --test"
    echo ""

elif [ "$AMD64_ONLY" = true ]; then
    print_header "Build GPU pour AMD64 uniquement"

    if [ -z "$DOCKER_USER" ]; then
        print_error "DOCKER_USER requis pour le build avec push"
        exit 1
    fi

    print_info "Plateforme: linux/amd64"
    print_info "Tags: ${DOCKER_USER}/fededge:${VERSION}-gpu, ${DOCKER_USER}/fededge:latest-gpu"
    print_info "Cela peut prendre 10-20 minutes..."
    echo ""

    # Afficher la commande
    print_info "Commande Docker buildx:"
    echo "  docker buildx build \\"
    echo "    --platform linux/amd64 \\"
    echo "    --file Dockerfile.gpu \\"
    echo "    --tag ${DOCKER_USER}/fededge:${VERSION}-gpu \\"
    echo "    --tag ${DOCKER_USER}/fededge:latest-gpu \\"
    echo "    --push \\"
    echo "    ."
    echo ""

    # Demander confirmation
    read -p "Continuer ? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Annulé par l'utilisateur"
        exit 0
    fi

    # Lancer le build
    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.gpu \
        --tag ${DOCKER_USER}/fededge:${VERSION}-gpu \
        --tag ${DOCKER_USER}/fededge:latest-gpu \
        --push \
        --progress=plain \
        .

    print_success "Build et push GPU (amd64) réussis !"

else
    print_header "Build multi-plateforme GPU (amd64 + arm64)"

    print_info "Plateformes: linux/amd64, linux/arm64"
    print_info "Tags: ${DOCKER_USER}/fededge:${VERSION}-gpu, ${DOCKER_USER}/fededge:latest-gpu"
    print_info "ATTENTION: Le build GPU multi-plateforme peut prendre 30-60 minutes"
    print_info "Pour amd64 uniquement (plus rapide), utilisez: ./build-multiplatform-gpu.sh --amd64-only"
    echo ""

    # Afficher la commande
    print_info "Commande Docker buildx:"
    echo "  docker buildx build \\"
    echo "    --platform linux/amd64,linux/arm64 \\"
    echo "    --file Dockerfile.gpu \\"
    echo "    --tag ${DOCKER_USER}/fededge:${VERSION}-gpu \\"
    echo "    --tag ${DOCKER_USER}/fededge:latest-gpu \\"
    echo "    --push \\"
    echo "    ."
    echo ""

    # Demander confirmation
    read -p "Continuer ? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Annulé par l'utilisateur"
        exit 0
    fi

    # Lancer le build
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --file Dockerfile.gpu \
        --tag ${DOCKER_USER}/fededge:${VERSION}-gpu \
        --tag ${DOCKER_USER}/fededge:latest-gpu \
        --push \
        --progress=plain \
        .

    print_success "Build et push GPU multi-plateforme réussis !"
fi

# ============================================================================
# Résumé final
# ============================================================================

if [ "$TEST_MODE" = false ]; then
    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image GPU a été construite et poussée avec succès !"
    echo ""
    echo "📊 Images disponibles :"
    echo "  - ${DOCKER_USER}/fededge:${VERSION}-gpu"
    echo "  - ${DOCKER_USER}/fededge:latest-gpu"
    echo ""

    if [ "$AMD64_ONLY" = true ]; then
        echo "🏗️  Plateforme supportée :"
        echo "  - linux/amd64 (NVIDIA GPU)"
    else
        echo "🏗️  Plateformes supportées :"
        echo "  - linux/amd64 (NVIDIA GPU)"
        echo "  - linux/arm64 (NVIDIA Jetson)"
    fi

    echo ""
    echo "📝 Pour tester :"
    echo "  docker pull ${DOCKER_USER}/fededge:latest-gpu"
    echo "  docker run -d --gpus all --name fededge \\"
    echo "    -p 8000:8000 -p 9001:9001 -p 9002:9002 \\"
    echo "    -v \$(pwd)/data:/app/data \\"
    echo "    ${DOCKER_USER}/fededge:latest-gpu"
    echo ""
    echo "💡 Configuration GPU :"
    echo "  - Détection automatique du GPU"
    echo "  - Pour forcer CPU : -e GPU_LAYERS=0"
    echo "  - Pour limiter les couches GPU : -e GPU_LAYERS=20"
    echo ""
fi
