#!/bin/bash

################################################################################
# FedEdge Docker Multi-Architecture Build Script
#
# Usage:
#   ./build-docker.sh                    # Build local (test)
#   ./build-docker.sh --push             # Build et push sur Docker Hub
#   ./build-docker.sh --version 1.0.2    # Spécifier une version
#   ./build-docker.sh --type cpu         # Build seulement CPU
#   ./build-docker.sh --type gpu         # Build seulement GPU
#   ./build-docker.sh --github           # Push aussi sur GitHub Container Registry
#
################################################################################

set -e  # Arrêter en cas d'erreur

# ============================================================================
# Configuration par défaut
# ============================================================================

VERSION="1.0.1"
DOCKER_USER="imedmagroune"
IMAGE_NAME="fededge"
PUSH=false
PUSH_GITHUB=false
BUILD_TYPE="all"  # all, cpu, gpu

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Fonctions utilitaires
# ============================================================================

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

# ============================================================================
# Parse arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --github)
            PUSH_GITHUB=true
            shift
            ;;
        --type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --version VERSION    Version à builder (défaut: 1.0.1)"
            echo "  --push              Push sur Docker Hub"
            echo "  --github            Push aussi sur GitHub Container Registry"
            echo "  --type TYPE         Type de build: all, cpu, gpu (défaut: all)"
            echo "  --help              Afficher ce message"
            echo ""
            echo "Exemples:"
            echo "  $0                           # Build local uniquement"
            echo "  $0 --push                    # Build et push Docker Hub"
            echo "  $0 --version 1.0.2 --push    # Build version 1.0.2 et push"
            echo "  $0 --type cpu --push         # Build seulement CPU"
            echo "  $0 --push --github           # Push sur Docker Hub et GitHub"
            exit 0
            ;;
        *)
            print_error "Option inconnue: $1"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
    esac
done

# ============================================================================
# Vérifications préalables
# ============================================================================

print_header "Vérifications préalables"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé"
    exit 1
fi
print_success "Docker installé: $(docker --version)"

# Vérifier Docker Buildx
if ! docker buildx version &> /dev/null; then
    print_error "Docker Buildx n'est pas disponible"
    exit 1
fi
print_success "Docker Buildx disponible: $(docker buildx version)"

# Vérifier l'authentification si push est demandé
if [ "$PUSH" = true ]; then
    if ! docker info | grep -q "Username: ${DOCKER_USER}"; then
        print_error "Vous devez vous authentifier à Docker Hub"
        echo "Exécutez: docker login"
        exit 1
    fi
    print_success "Authentifié sur Docker Hub: ${DOCKER_USER}"
fi

if [ "$PUSH_GITHUB" = true ]; then
    if ! docker info | grep -q "ghcr.io"; then
        print_info "Authentification GitHub Container Registry nécessaire"
        echo "Exécutez: echo \$GITHUB_TOKEN | docker login ghcr.io -u ${DOCKER_USER} --password-stdin"
    fi
fi

# Créer/vérifier le builder
print_info "Configuration du builder multi-architecture..."
if ! docker buildx ls | grep -q "fededge-builder"; then
    docker buildx create --name fededge-builder --use
    print_success "Builder 'fededge-builder' créé"
else
    docker buildx use fededge-builder
    print_success "Builder 'fededge-builder' activé"
fi

docker buildx inspect --bootstrap > /dev/null 2>&1
print_success "Builder prêt"

# ============================================================================
# Configuration des builds
# ============================================================================

print_header "Configuration du build"

echo "Version:         ${VERSION}"
echo "Docker User:     ${DOCKER_USER}"
echo "Image:           ${IMAGE_NAME}"
echo "Type de build:   ${BUILD_TYPE}"
echo "Push Docker Hub: ${PUSH}"
echo "Push GitHub:     ${PUSH_GITHUB}"
echo ""

# ============================================================================
# Fonction de build
# ============================================================================

build_image() {
    local dockerfile=$1
    local platforms=$2
    local tags=$3
    local description=$4

    print_header "Build: ${description}"

    local build_args="--file ${dockerfile} --platform ${platforms}"

    # Ajouter les tags
    for tag in $tags; do
        if [ "$PUSH" = true ]; then
            build_args="${build_args} --tag ${DOCKER_USER}/${IMAGE_NAME}:${tag}"
        else
            build_args="${build_args} --tag ${IMAGE_NAME}:${tag}"
        fi

        if [ "$PUSH_GITHUB" = true ]; then
            build_args="${build_args} --tag ghcr.io/${DOCKER_USER}/${IMAGE_NAME}:${tag}"
        fi
    done

    # Push ou load
    if [ "$PUSH" = true ] || [ "$PUSH_GITHUB" = true ]; then
        build_args="${build_args} --push"
    else
        # Pour les builds locaux multi-arch, on ne peut pas utiliser --load
        # On utilise --output type=image,push=false à la place
        if [[ "$platforms" == *","* ]]; then
            print_info "Build multi-architecture local (pas de --load possible)"
            build_args="${build_args} --output type=image,push=false"
        else
            build_args="${build_args} --load"
        fi
    fi

    # Build
    print_info "Commande: docker buildx build ${build_args} ."
    if eval "docker buildx build ${build_args} ."; then
        print_success "Build ${description} réussi"

        # Afficher les tags créés
        echo ""
        echo "Tags créés:"
        for tag in $tags; do
            if [ "$PUSH" = true ]; then
                echo "  - ${DOCKER_USER}/${IMAGE_NAME}:${tag}"
            else
                echo "  - ${IMAGE_NAME}:${tag}"
            fi

            if [ "$PUSH_GITHUB" = true ]; then
                echo "  - ghcr.io/${DOCKER_USER}/${IMAGE_NAME}:${tag}"
            fi
        done
        echo ""

        return 0
    else
        print_error "Échec du build ${description}"
        return 1
    fi
}

# ============================================================================
# Builds
# ============================================================================

BUILD_SUCCESS=true

# Build CPU-FULL (recommandé pour production)
if [ "$BUILD_TYPE" = "all" ] || [ "$BUILD_TYPE" = "cpu" ]; then
    print_header "BUILD 1/3 : CPU-FULL (OpenBLAS) - Production"

    PLATFORMS="linux/amd64,linux/arm64"
    TAGS="${VERSION} ${VERSION}-cpu latest"

    if [ "$VERSION" != "${VERSION%-beta}" ]; then
        TAGS="${TAGS} ${VERSION%-beta}"
    fi

    if ! build_image "Dockerfile.cpu-full" "$PLATFORMS" "$TAGS" "CPU-FULL (OpenBLAS)"; then
        BUILD_SUCCESS=false
    fi

    sleep 2
fi

# Build CPU-PURE (compatibilité maximale)
if [ "$BUILD_TYPE" = "all" ] || [ "$BUILD_TYPE" = "cpu" ]; then
    print_header "BUILD 2/3 : CPU-PURE - Compatibilité Maximale"

    PLATFORMS="linux/amd64,linux/arm64,linux/arm/v7"
    TAGS="${VERSION}-pure"

    if ! build_image "Dockerfile.cpu-pure" "$PLATFORMS" "$TAGS" "CPU-PURE"; then
        BUILD_SUCCESS=false
    fi

    sleep 2
fi

# Build GPU (NVIDIA CUDA)
if [ "$BUILD_TYPE" = "all" ] || [ "$BUILD_TYPE" = "gpu" ]; then
    print_header "BUILD 3/3 : GPU (CUDA 12.2) - NVIDIA"

    PLATFORMS="linux/amd64"
    TAGS="${VERSION}-gpu gpu"

    if ! build_image "Dockerfile.gpu-full" "$PLATFORMS" "$TAGS" "GPU-CUDA"; then
        BUILD_SUCCESS=false
    fi
fi

# ============================================================================
# Résumé final
# ============================================================================

print_header "Résumé du Build"

if [ "$BUILD_SUCCESS" = true ]; then
    print_success "Tous les builds ont réussi !"

    echo ""
    echo "Images disponibles:"

    if [ "$PUSH" = true ]; then
        echo ""
        echo "Docker Hub (https://hub.docker.com/r/${DOCKER_USER}/${IMAGE_NAME}):"
        echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}"
        echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:latest"

        if [ "$BUILD_TYPE" = "all" ] || [ "$BUILD_TYPE" = "cpu" ]; then
            echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}-cpu"
            echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}-pure"
        fi

        if [ "$BUILD_TYPE" = "all" ] || [ "$BUILD_TYPE" = "gpu" ]; then
            echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}-gpu"
        fi
    else
        echo ""
        echo "Images locales:"
        docker images | grep "${IMAGE_NAME}" | head -10
    fi

    if [ "$PUSH_GITHUB" = true ]; then
        echo ""
        echo "GitHub Container Registry:"
        echo "  docker pull ghcr.io/${DOCKER_USER}/${IMAGE_NAME}:${VERSION}"
        echo "  docker pull ghcr.io/${DOCKER_USER}/${IMAGE_NAME}:latest"
    fi

    echo ""
    print_info "Pour tester l'image:"
    if [ "$PUSH" = true ]; then
        echo "  docker run -d -p 8000:8000 -v \$(pwd)/data:/app/data ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}"
    else
        echo "  docker run -d -p 8000:8000 -v \$(pwd)/data:/app/data ${IMAGE_NAME}:${VERSION}"
    fi
    echo "  curl http://localhost:8000/health"

    exit 0
else
    print_error "Certains builds ont échoué"
    exit 1
fi
