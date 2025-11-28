"""
HTML Cleaner - Nettoie le contenu HTML des articles de news
Supprime les balises HTML, décode les entités HTML, et formate le texte proprement
"""

import re
import html
from typing import Optional

def clean_html_content(content: str) -> str:
    """
    Nettoie le contenu HTML d'un article
    
    Args:
        content: Contenu HTML brut
        
    Returns:
        Texte nettoyé sans balises HTML
    """
    if not content or not isinstance(content, str):
        return ""
    
    try:
        # 1. Décoder les entités HTML (&#039; -> ', &amp; -> &, etc.)
        cleaned = html.unescape(content)
        
        # 2. Supprimer les balises de script et style avec leur contenu
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # 3. Supprimer les commentaires HTML
        cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
        
        # 4. Remplacer les balises de saut de ligne par des espaces
        cleaned = re.sub(r'<br\s*/?>', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</?p[^>]*>', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</?div[^>]*>', ' ', cleaned, flags=re.IGNORECASE)
        
        # 5. Supprimer les balises d'image et médias (souvent inutiles pour le texte)
        cleaned = re.sub(r'<img[^>]*>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<video[^>]*>.*?</video>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<audio[^>]*>.*?</audio>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # 6. Supprimer toutes les autres balises HTML restantes
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # 7. Nettoyer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 8. Supprimer les espaces en début et fin
        cleaned = cleaned.strip()
        
        # 9. Limiter la longueur si trop long (éviter les articles géants)
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."
        
        return cleaned
        
    except Exception as e:
        print(f"Erreur lors du nettoyage HTML: {e}")
        # Fallback: au moins supprimer les balises de base
        try:
            fallback = re.sub(r'<[^>]+>', '', content)
            return fallback.strip()[:2000]
        except:
            return content[:500] if len(content) > 500 else content

def clean_article_title(title: str) -> str:
    """
    Nettoie le titre d'un article
    
    Args:
        title: Titre brut pouvant contenir des entités HTML
        
    Returns:
        Titre nettoyé
    """
    if not title or not isinstance(title, str):
        return ""
    
    try:
        # Décoder les entités HTML
        cleaned = html.unescape(title)
        
        # Supprimer les balises HTML si présentes
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Nettoyer les espaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Limiter la longueur du titre
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + "..."
        
        return cleaned
        
    except Exception as e:
        print(f"Erreur lors du nettoyage du titre: {e}")
        return title[:200] if len(title) > 200 else title

def extract_text_preview(content: str, max_length: int = 300) -> str:
    """
    Extrait un aperçu propre du contenu pour l'affichage
    
    Args:
        content: Contenu HTML ou texte brut
        max_length: Longueur maximale de l'aperçu
        
    Returns:
        Aperçu nettoyé du contenu
    """
    if not content:
        return ""
    
    # Nettoyer le HTML
    clean_content = clean_html_content(content)
    
    # Créer un aperçu
    if len(clean_content) <= max_length:
        return clean_content
    
    # Couper au dernier espace complet avant la limite
    preview = clean_content[:max_length]
    last_space = preview.rfind(' ')
    
    if last_space > max_length * 0.8:  # Si on trouve un espace proche de la fin
        preview = preview[:last_space]
    
    return preview + "..."

def clean_url(url: str) -> Optional[str]:
    """
    Nettoie et valide une URL
    
    Args:
        url: URL brute
        
    Returns:
        URL nettoyée ou None si invalide
    """
    if not url or not isinstance(url, str):
        return None
    
    try:
        # Supprimer les espaces
        url = url.strip()
        
        # Vérifier que c'est une URL valide
        if not (url.startswith('http://') or url.startswith('https://')):
            return None
        
        # Supprimer les paramètres de tracking courants (optionnel)
        # utm_source, utm_medium, etc.
        url_parts = url.split('?')
        if len(url_parts) > 1:
            base_url = url_parts[0]
            params = url_parts[1].split('&')
            
            # Garder seulement les paramètres qui ne sont pas du tracking
            clean_params = []
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
            
            for param in params:
                param_name = param.split('=')[0].lower()
                if param_name not in tracking_params:
                    clean_params.append(param)
            
            if clean_params:
                url = base_url + '?' + '&'.join(clean_params)
            else:
                url = base_url
        
        return url
        
    except Exception as e:
        print(f"Erreur lors du nettoyage URL: {e}")
        return url if url.startswith(('http://', 'https://')) else None

def clean_article_data(article_data: dict) -> dict:
    """
    Nettoie toutes les données d'un article
    
    Args:
        article_data: Dictionnaire avec les données de l'article
        
    Returns:
        Dictionnaire avec les données nettoyées
    """
    cleaned = article_data.copy()
    
    # Nettoyer le titre
    if 'title' in cleaned:
        cleaned['title'] = clean_article_title(cleaned['title'])
    
    # Nettoyer la description/contenu
    if 'description' in cleaned:
        cleaned['description'] = clean_html_content(cleaned['description'])
    
    if 'content' in cleaned:
        cleaned['content'] = clean_html_content(cleaned['content'])
    
    # Nettoyer l'URL
    if 'url' in cleaned:
        cleaned['url'] = clean_url(cleaned['url'])
    
    # Nettoyer la source (au cas où)
    if 'source' in cleaned:
        source = cleaned['source']
        if isinstance(source, str):
            cleaned['source'] = re.sub(r'[<>]', '', source).strip()
    
    return cleaned

# Fonction de test pour valider le nettoyage
def test_html_cleaner():
    """Test des fonctions de nettoyage HTML"""
    print("🧪 Test du HTML Cleaner")
    print("=" * 50)
    
    # Test 1: Contenu HTML complexe
    html_content = '''<p style="float: right; margin: 0 0 10px 15px; width: 240px;"><img alt="Test" src="https://example.com/image.jpg"></p>
    <h2>Titre Important</h2>
    <p>Ceci est un <b>test</b> avec des <a href="http://example.com">liens</a> et du <em>texte formaté</em>.</p>
    <script>alert('malicious');</script>
    <style>.hidden { display: none; }</style>
    <!-- Commentaire HTML -->'''
    
    cleaned = clean_html_content(html_content)
    print(f"HTML original: {html_content[:100]}...")
    print(f"HTML nettoyé: {cleaned}")
    
    # Test 2: Entités HTML
    title_with_entities = "Citigroup, JP Morgan, Goldman Sachs lead TradFi&#039;s blockchain charge: Ripple"
    cleaned_title = clean_article_title(title_with_entities)
    print(f"\nTitre original: {title_with_entities}")
    print(f"Titre nettoyé: {cleaned_title}")
    
    # Test 3: URL avec tracking
    url_with_tracking = "https://cointelegraph.com/news/test?utm_source=rss_feed&utm_medium=rss&utm_campaign=rss_partner_inbound"
    cleaned_url = clean_url(url_with_tracking)
    print(f"\nURL originale: {url_with_tracking}")
    print(f"URL nettoyée: {cleaned_url}")
    
    print("\n✅ Tests terminés")

if __name__ == "__main__":
    test_html_cleaner()