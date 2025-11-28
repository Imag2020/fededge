#!/bin/bash

################################################################################
# Script de Build Multi-Plateforme - FedEdge
#
# Ce script construit et pousse l'image Docker pour amd64 et arm64
#
# Usage:
#   export DOCKER_USER=votre_username
#   export VERSION=v1.0.0
#   ./build-multiplatform.sh              # Build et push
#   ./build-multiplatform.sh --test       # Build test local sans push
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
if [ "$1" = "--test" ]; then
    TEST_MODE=true
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
    echo "  ./build-multiplatform.sh --test"
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
    print_header "Build test local (sans push)"

    print_info "Construction pour linux/amd64 uniquement..."
    print_info "Cela peut prendre plusieurs minutes..."

    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.cpu-full \
        --tag fededge:test \
        --load \
        .

    print_success "Build test réussi !"

    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image de test a été construite avec succès !"
    echo ""
    echo "📊 Image créée : fededge:test"
    echo ""
    echo "📝 Pour tester :"
    echo "  docker run -d --name fededge-test -p 8000:8000 -p 9001:9001 -p 9002:9002 -v \$(pwd)/data:/app/data fededge:test"
    echo ""
    echo "Pour le build multi-plateforme complet, relancez sans --test"
    echo ""

else
    print_header "Build multi-plateforme (amd64 + arm64)"

    print_info "Plateformes: linux/amd64, linux/arm64"
    print_info "Tags: ${DOCKER_USER}/fededge:${VERSION}, ${DOCKER_USER}/fededge:latest"
    print_info "Cela peut prendre 15-30 minutes (compilation pour 2 architectures)..."
    echo ""

    # Afficher la commande qui va être exécutée
    print_info "Commande Docker buildx:"
    echo "  docker buildx build \\"
    echo "    --platform linux/amd64,linux/arm64 \\"
    echo "    --file Dockerfile.cpu-full \\"
    echo "    --tag ${DOCKER_USER}/fededge:${VERSION} \\"
    echo "    --tag ${DOCKER_USER}/fededge:latest \\"
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
        --file Dockerfile.cpu-full \
        --tag ${DOCKER_USER}/fededge:${VERSION} \
        --tag ${DOCKER_USER}/fededge:${VERSION} \
        --push \
        --progress=plain \
        .

    print_success "Build et push réussis !"

    echo ""
    print_header "Résumé"
    echo ""
    echo "🎉 L'image multi-plateforme a été construite et poussée avec succès !"
    echo ""
    echo "📊 Images disponibles :"
    echo "  - ${DOCKER_USER}/fededge:${VERSION}"
    echo "  - ${DOCKER_USER}/fededge:latest"
    echo ""
    echo "🏗️  Plateformes supportées :"
    echo "  - linux/amd64"
    echo "  - linux/arm64"
    echo ""
    echo "📝 Pour tester :"
    echo "  docker pull ${DOCKER_USER}/fededge:latest"
    echo "  docker run -d --name fededge -p 8000:8000 -p 9001:9001 -p 9002:9002 -v \$(pwd)/data:/app/data ${DOCKER_USER}/fededge:latest"
    echo ""
fi
