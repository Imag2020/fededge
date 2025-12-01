#!/bin/bash

# Script pour pousser FedEdge sur GitHub
# Repository: https://github.com/Imag2020/fededge
# Version: v0.0.1

set -e

REPO_URL="https://github.com/Imag2020/fededge.git"
VERSION="v0.0.1"

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Push FedEdge vers GitHub ===${NC}"

# Vérifier si le token est fourni
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Erreur: Variable GITHUB_TOKEN non définie${NC}"
    echo "Usage: GITHUB_TOKEN=votre_token ./push-to-github.sh"
    exit 1
fi

# Configurer le remote avec le token
echo -e "${YELLOW}Configuration du remote GitHub...${NC}"
REMOTE_URL="https://imag2020:${GITHUB_TOKEN}@github.com/Imag2020/fededge.git"

if git remote | grep -q "^origin$"; then
    git remote set-url origin "$REMOTE_URL"
    echo "Remote 'origin' mis à jour"
else
    git remote add origin "$REMOTE_URL"
    echo "Remote 'origin' ajouté"
fi

# Créer un .gitignore temporaire pour exclure les .md sauf README.md
echo -e "${YELLOW}Configuration des fichiers à exclure...${NC}"
cat > .gitignore.temp << 'EOF'
# Exclure tous les fichiers .md sauf README.md
*.md
!README.md

# Exclure les notebooks
*.ipynb

# Fichiers Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.venv/
venv/
ENV/

# Données et logs
data/
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.env.local
EOF

# Backup du .gitignore existant si présent
if [ -f .gitignore ]; then
    cp .gitignore .gitignore.backup
fi

# Utiliser le nouveau .gitignore
mv .gitignore.temp .gitignore

# Ajouter les fichiers
echo -e "${YELLOW}Ajout des fichiers au staging...${NC}"
git add .

# Retirer les fichiers .md sauf README.md s'ils sont stagés
echo -e "${YELLOW}Retrait des fichiers markdown (sauf README.md)...${NC}"
for file in *.md; do
    if [ "$file" != "README.md" ] && [ -f "$file" ]; then
        git reset HEAD "$file" 2>/dev/null || true
        echo "Exclu: $file"
    fi
done

# Retirer les notebooks
for file in *.ipynb; do
    if [ -f "$file" ]; then
        git reset HEAD "$file" 2>/dev/null || true
        echo "Exclu: $file"
    fi
done

# Vérifier s'il y a des changements à commiter
if git diff --cached --quiet; then
    echo -e "${YELLOW}Aucun changement à commiter${NC}"
else
    # Créer le commit
    echo -e "${YELLOW}Création du commit...${NC}"
    git commit -m "Release v${VERSION} - FedEdge Initial Release

- Backend avec agents fédérés et trading
- Frontend avec dashboard interactif
- Support Docker avec clean-build.sh
- Documentation README incluse"
fi

# Créer le tag si nécessaire
if git tag | grep -q "^${VERSION}$"; then
    echo -e "${YELLOW}Tag ${VERSION} existe déjà${NC}"
else
    echo -e "${YELLOW}Création du tag ${VERSION}...${NC}"
    git tag -a "${VERSION}" -m "Version ${VERSION} - Initial Release"
fi

# Pousser vers GitHub
echo -e "${YELLOW}Push vers GitHub...${NC}"
git push -u origin main

# Pousser les tags
echo -e "${YELLOW}Push des tags...${NC}"
git push origin --tags

# Restaurer le .gitignore original si backup existe
if [ -f .gitignore.backup ]; then
    mv .gitignore.backup .gitignore
    echo "Gitignore original restauré"
fi

# Nettoyer l'URL avec le token de l'historique
git remote set-url origin "$REPO_URL"

echo -e "${GREEN}=== ✓ Push terminé avec succès ===${NC}"
echo -e "${GREEN}Repository: ${REPO_URL}${NC}"
echo -e "${GREEN}Version: ${VERSION}${NC}"
echo ""
echo -e "${YELLOW}Note: Le token a été retiré de la configuration git pour des raisons de sécurité${NC}"
