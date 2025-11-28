#!/bin/bash

################################################################################
# Script de Build GPU Simple - FedEdge
#
# Build l'image GPU pour AMD64 (NVIDIA GPU)
# Plus simple et plus rapide que le multi-plateforme
#
# Usage:
#   export DOCKER_USER=votre_username
#   export VERSION=v1.0.0
#   ./build-gpu.sh              # Build et push
#   ./build-gpu.sh --local      # Build local sans push
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
LOCAL_ONLY=false
if [ "$1" = "--local" ]; then
    LOCAL_ONLY=true
fi

# ============================================================================
# Configuration
# ============================================================================

print_header "Configuration du build GPU"

if [ -z "$DOCKER_USER" ] && [ "$LOCAL_ONLY" = false ]; then
    print_error "La variable DOCKER_USER n'est pas définie"
    echo ""
    echo "Définissez-la avec:"
    echo "  export DOCKER_USER=votre_username"
    echo ""
    echo "Ou utilisez le mode local:"
    echo "  ./build-gpu.sh --local"
    exit 1
fi

if [ -z "$VERSION" ]; then
    VERSION="latest"
    print_info "VERSION non définie, utilisation de 'latest'"
else
    print_success "VERSION: $VERSION"
fi

if [ "$LOCAL_ONLY" = false ]; then
    print_success "DOCKER_USER: $DOCKER_USER"
    IMAGE_TAG="${DOCKER_USER}/fededge:${VERSION}-gpu"
    IMAGE_TAG_LATEST="${DOCKER_USER}/fededge:latest-gpu"
else
    IMAGE_TAG="fededge:gpu"
    IMAGE_TAG_LATEST="fededge:latest-gpu"
fi

print_success "Image tags: $IMAGE_TAG, $IMAGE_TAG_LATEST"

# ============================================================================
# Vérification buildx
# ============================================================================

print_header "Vérification de Docker buildx"

if ! docker buildx version > /dev/null 2>&1; then
    print_error "Docker buildx n'est pas installé"
    exit 1
fi

print_success "Docker buildx disponible"

# Vérifier/créer le builder
if ! docker buildx ls | grep -q "fededge-builder"; then
    print_info "Création du builder..."
    docker buildx create --name fededge-builder --use --driver-opt network=host
    print_success "Builder créé"
else
    print_info "Utilisation du builder existant"
    docker buildx use fededge-builder
fi

docker buildx inspect --bootstrap > /dev/null 2>&1
print_success "Builder prêt"

# ============================================================================
# Build de l'image
# ============================================================================

print_header "Build de l'image GPU (AMD64)"

print_info "Plateforme: linux/amd64"
print_info "Dockerfile: Dockerfile.gpu"
print_info "Temps estimé: 10-20 minutes"
echo ""

if [ "$LOCAL_ONLY" = true ]; then
    print_info "Mode LOCAL - l'image sera chargée localement"
    echo ""

    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.gpu \
        --tag "$IMAGE_TAG" \
        --tag "$IMAGE_TAG_LATEST" \
        --load \
        .

    BUILD_STATUS=$?
else
    print_info "Mode PUSH - l'image sera poussée vers Docker Hub"
    echo ""

    # Confirmation
    read -p "Continuer avec le build et push ? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Annulé par l'utilisateur"
        exit 0
    fi

    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.gpu \
        --tag "$IMAGE_TAG" \
        --tag "$IMAGE_TAG_LATEST" \
        --push \
        --progress=plain \
        .

    BUILD_STATUS=$?
fi

# ============================================================================
# Résultat
# ============================================================================

if [ $BUILD_STATUS -eq 0 ]; then
    echo ""
    print_header "✅ Build réussi !"
    echo ""

    if [ "$LOCAL_ONLY" = true ]; then
        echo "📊 Image locale créée :"
        echo "  - $IMAGE_TAG"
        echo "  - $IMAGE_TAG_LATEST"
        echo ""
        echo "📝 Pour tester (nécessite NVIDIA GPU) :"
        echo "  docker run -d --gpus all --name fededge-gpu \\"
        echo "    -p 8000:8000 -p 9001:9001 -p 9002:9002 \\"
        echo "    -v \$(pwd)/data:/app/data \\"
        echo "    $IMAGE_TAG"
    else
        echo "📊 Images disponibles sur Docker Hub :"
        echo "  - $IMAGE_TAG"
        echo "  - $IMAGE_TAG_LATEST"
        echo ""
        echo "🏗️  Plateforme : linux/amd64 (NVIDIA GPU)"
        echo ""
        echo "📝 Pour utiliser :"
        echo "  docker pull $IMAGE_TAG_LATEST"
        echo "  docker run -d --gpus all --name fededge \\"
        echo "    -p 8000:8000 -p 9001:9001 -p 9002:9002 \\"
        echo "    -v \$(pwd)/data:/app/data \\"
        echo "    $IMAGE_TAG_LATEST"
    fi

    echo ""
    echo "💡 Configuration GPU :"
    echo "  - Détection automatique activée"
    echo "  - Pour forcer CPU : -e GPU_LAYERS=0"
    echo "  - Pour limiter GPU : -e GPU_LAYERS=20"
    echo ""

    # Afficher la taille de l'image
    if [ "$LOCAL_ONLY" = true ]; then
        SIZE=$(docker images "$IMAGE_TAG" --format "{{.Size}}" 2>/dev/null || echo "N/A")
        if [ "$SIZE" != "N/A" ]; then
            echo "📦 Taille de l'image : $SIZE"
        fi
    fi

else
    echo ""
    print_header "❌ Build échoué"
    echo ""
    print_error "Le build a échoué avec le code $BUILD_STATUS"
    echo ""
    echo "💡 Suggestions :"
    echo "  - Vérifiez les logs ci-dessus"
    echo "  - Vérifiez l'espace disque : df -h /var"
    echo "  - Nettoyez le cache : docker buildx prune -af"
    echo ""
    exit $BUILD_STATUS
fi
