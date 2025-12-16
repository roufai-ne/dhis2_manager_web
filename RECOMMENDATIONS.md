# 📋 DHIS2 Manager - Recommandations d'Amélioration

**Date:** 2025-12-09
**Version analysée:** v5.0 Web Edition
**Score global:** ⭐⭐⭐ (2.8/5)

## ⚠️ STATUT: NON PRÊT POUR LA PRODUCTION

L'application nécessite des corrections de sécurité critiques avant tout déploiement.

---

## 🔴 CORRECTIONS CRITIQUES (À FAIRE IMMÉDIATEMENT)

### 1. SECRET_KEY Sécurisée ✅ CORRIGÉ
**Fichier:** `app/config.py`

```python
# ❌ AVANT
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'

# ✅ APRÈS
import secrets

def generate_secret_key() -> str:
    return secrets.token_hex(32)

SECRET_KEY = os.environ.get('SECRET_KEY') or generate_secret_key()

# Validation en production
def validate_production_config():
    if os.environ.get('FLASK_ENV') == 'production':
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY requise en production!")
```

**Générer une clé:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Protection Path Traversal ⚠️ À CORRIGER
**Fichier:** `app/services/session_manager.py:16-18`

```python
# ❌ VULNÉRABILITÉ ACTUELLE
def get_session_dir(session_id: str) -> Path:
    return Path(f"sessions/{session_id}")  # Pas de validation!

# ✅ CORRECTION REQUISE
import re
SESSIONS_BASE_PATH = Path("sessions").resolve()

def validate_session_id(session_id: str) -> bool:
    if not re.match(r'^[a-zA-Z0-9]+$', session_id):
        return False
    if not (16 <= len(session_id) <= 64):
        return False
    return True

def get_session_dir(session_id: str) -> Path:
    if not validate_session_id(session_id):
        raise ValueError(f"Invalid session ID: {session_id}")

    session_path = (SESSIONS_BASE_PATH / session_id).resolve()

    # Vérifier qu'on reste dans sessions/
    if not str(session_path).startswith(str(SESSIONS_BASE_PATH)):
        raise ValueError("Path traversal detected")

    return session_path
```

### 3. Protection CSRF ⚠️ À AJOUTER
**Fichier:** `app/__init__.py`

```python
# Ajouter au requirements.txt
Flask-WTF==1.2.1

# Dans app/__init__.py
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)

    # Configuration
    app.config.from_object(config[config_name])

    # CSRF Protection
    csrf.init_app(app)

    return app
```

**Dans base.html:**
```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

**Dans JavaScript:**
```javascript
// Ajouter aux requêtes POST
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

### 4. Headers de Sécurité ⚠️ À AJOUTER
**Fichier:** `app/__init__.py`

```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # CSP - Adapter selon vos besoins
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "img-src 'self' data:;"
    )

    return response
```

### 5. Rate Limiting ⚠️ À AJOUTER
**Fichier:** `app/__init__.py`

```python
# requirements.txt
Flask-Limiter==3.5.0

# app/__init__.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Sur routes sensibles
@bp.route('/api/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file():
    ...
```

### 6. Validation de Fichiers ⚠️ À AMÉLIORER
**Fichier:** `app/services/file_handler.py`

```python
# requirements.txt
python-magic==0.4.27
python-magic-bin==0.4.14  # Pour Windows

# Validation MIME
import magic

def validate_file_content(filepath: Path, expected_type: str) -> bool:
    mime = magic.from_file(str(filepath), mime=True)

    if expected_type == 'json':
        return mime == 'application/json'
    elif expected_type == 'excel':
        return mime in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]

    return False

def save_upload_file(file, session_id: str, allowed_extensions: set) -> Tuple[bool, str]:
    if not allowed_file(file.filename, allowed_extensions):
        return False, "Type de fichier non autorisé"

    # Sauvegarder temporairement
    temp_path = session_dir / filename
    file.save(str(temp_path))

    # Valider le contenu MIME
    file_type = 'json' if filename.endswith('.json') else 'excel'
    if not validate_file_content(temp_path, file_type):
        temp_path.unlink()
        return False, "Contenu du fichier invalide"

    return True, str(temp_path)
```

### 7. Gestion d'Erreurs Globale ⚠️ À AJOUTER
**Fichier:** `app/__init__.py`

```python
@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"Bad Request: {error}")
    return jsonify({'error': 'Requête invalide'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"Forbidden: {error}")
    return jsonify({'error': 'Accès interdit'}), 403

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Server Error: {error}', exc_info=True)
    return jsonify({'error': 'Erreur serveur interne'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception('Unhandled exception')

    # Ne pas exposer les détails en production
    if app.config['DEBUG']:
        return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Une erreur est survenue'}), 500
```

### 8. Sanitization Excel ⚠️ À AJOUTER
**Fichier:** `app/services/data_calculator.py`

```python
def sanitize_excel_value(value: str) -> str:
    """
    Prévient l'injection de formules Excel

    Les formules commençant par =, +, -, @, \t, \r sont dangereuses
    """
    value_str = str(value).strip()

    if value_str and value_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value_str  # Préfixe qui force le texte

    return value_str

# Dans create_data_values:
data_value = {
    'dataElement': str(row['_dataElement']).strip(),
    'value': sanitize_excel_value(value),  # ✅ Sanitizé
    ...
}
```

---

## 🟡 AMÉLIORATIONS IMPORTANTES (Semaine 1-2)

### 9. Fichier .env dans gitignore
```bash
# Vérifier que .env est ignoré
echo ".env" >> .gitignore

# SUPPRIMER le .env actuel du repo (ATTENTION aux secrets!)
git rm --cached .env
git commit -m "Remove .env from repository"
```

### 10. Configuration Production
**Fichier:** `run.py`

```python
# ❌ NE JAMAIS faire ça en production!
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# ✅ Utiliser un serveur WSGI
# Créer wsgi.py:
from app import create_app
import os

application = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == "__main__":
    application.run()
```

**Déploiement:**
```bash
# Avec Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 300 wsgi:application

# Avec uWSGI
uwsgi --http 0.0.0.0:8000 --wsgi-file wsgi.py --callable application
```

### 11. Validation Pydantic
```python
# requirements.txt
pydantic==2.5.0

# app/schemas.py (nouveau fichier)
from pydantic import BaseModel, validator, Field
from typing import List

class TemplateRequest(BaseModel):
    dataset_id: str = Field(..., min_length=11, max_length=11)
    org_unit_ids: List[str] = Field(..., min_items=1)
    period: str = Field(..., pattern=r'^\d{4}(-\d{2})?(-\d{2})?$')
    period_type: str

    @validator('org_unit_ids')
    def validate_org_ids(cls, v):
        if not all(len(id) == 11 for id in v):
            raise ValueError('IDs d\'organisation invalides')
        return v

# Dans les routes:
from app.schemas import TemplateRequest

@bp.route('/api/generate', methods=['POST'])
def generate_template():
    try:
        request_data = TemplateRequest(**request.get_json())
        # request_data est validé!
    except ValidationError as e:
        return jsonify({'error': 'Données invalides', 'details': e.errors()}), 400
```

### 12. Tests de Sécurité
**Fichier:** `tests/test_security.py`

```python
import pytest

def test_path_traversal_prevention():
    """Teste la protection contre path traversal"""
    with pytest.raises(ValueError):
        get_session_dir("../../etc/passwd")

    with pytest.raises(ValueError):
        get_session_dir("..%2F..%2Fetc%2Fpasswd")

def test_csrf_protection(client):
    """Teste que CSRF est activé"""
    response = client.post('/configuration/api/upload')
    assert response.status_code == 400  # CSRF token manquant

def test_rate_limiting(client):
    """Teste le rate limiting"""
    # Faire 15 requêtes rapidement
    for i in range(15):
        response = client.post('/api/upload')

    # La dernière devrait être bloquée
    assert response.status_code == 429

def test_file_upload_validation(client):
    """Teste la validation de fichiers"""
    # Fichier avec mauvaise extension mais bon MIME
    fake_json = (io.BytesIO(b'malicious code'), 'hack.exe')
    response = client.post('/configuration/api/upload',
                          data={'file': fake_json})
    assert response.status_code == 400
```

---

## 🟢 OPTIMISATIONS (Semaine 3-4)

### 13. Logs Structurés
```python
# requirements.txt
python-json-logger==2.0.7

# Configuration logging
import logging
from pythonjsonlogger import jsonlogger

formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)

handler = RotatingFileHandler('logs/app.json')
handler.setFormatter(formatter)

# Filtrer données sensibles
class SensitiveFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'SECRET_KEY=\w+', 'SECRET_KEY=***', record.msg)
        return True

handler.addFilter(SensitiveFilter())
```

### 14. Monitoring avec Prometheus
```python
# requirements.txt
prometheus-flask-exporter==0.22.4

# app/__init__.py
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
metrics.info('dhis2_manager_info', 'DHIS2 Manager', version='5.0.0')

# Métriques custom
from prometheus_client import Counter, Histogram

upload_counter = Counter('uploads_total', 'Uploads', ['status', 'type'])
processing_time = Histogram('processing_seconds', 'Processing time')

# Dans les routes:
@processing_time.time()
def process_file():
    ...
    upload_counter.labels(status='success', type='excel').inc()
```

### 15. Healthcheck Détaillé
```python
@bp.route('/health', methods=['GET'])
def health():
    checks = {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '5.0.0',
        'checks': {
            'sessions_dir': Path('sessions').exists(),
            'logs_dir': Path('logs').exists(),
            'disk_space': shutil.disk_usage('/').free > 1_000_000_000,  # 1GB
            'memory': psutil.virtual_memory().percent < 90
        }
    }

    all_ok = all(checks['checks'].values())
    status_code = 200 if all_ok else 503

    return jsonify(checks), status_code
```

---

## 📦 NOUVELLES DÉPENDANCES REQUISES

```txt
# Sécurité
Flask-WTF==1.2.1
Flask-Limiter==3.5.0
python-magic==0.4.27
python-magic-bin==0.4.14

# Validation
pydantic==2.5.0

# Logging & Monitoring
python-json-logger==2.0.7
prometheus-flask-exporter==0.22.4

# Serveur Production
gunicorn==21.2.0
```

---

## ✅ CHECKLIST PRÉ-DÉPLOIEMENT

### Sécurité
- [ ] SECRET_KEY générée et sécurisée
- [ ] Path traversal corrigé
- [ ] CSRF activé et testé
- [ ] Rate limiting configuré
- [ ] Headers de sécurité présents
- [ ] Validation fichiers MIME
- [ ] Sanitization Excel
- [ ] .env hors du repo

### Configuration
- [ ] DEBUG=False en production
- [ ] Variables d'environnement documentées
- [ ] Serveur WSGI configuré (Gunicorn/uWSGI)
- [ ] Logs avec rotation
- [ ] Session cleanup automatique

### Tests
- [ ] Tests unitaires (>70% couverture)
- [ ] Tests de sécurité
- [ ] Tests d'intégration
- [ ] Tests de charge

### Monitoring
- [ ] Healthcheck fonctionnel
- [ ] Métriques Prometheus
- [ ] Logs centralisés
- [ ] Alertes configurées

---

## 📈 ROADMAP

### Phase 1: Sécurité (Semaine 1-2) ⚠️ URGENT
- ✅ Configuration sécurisée
- ⚠️ Path traversal
- ⚠️ CSRF protection
- ⚠️ Headers sécurité
- ⚠️ Rate limiting
- ⚠️ Validation fichiers

### Phase 2: Fiabilité (Semaine 3-4)
- Tests complets
- Gestion d'erreurs
- Logs structurés
- Monitoring basique

### Phase 3: Performance (Mois 2)
- Cache Redis
- Compression Gzip
- Optimisation queries
- CDN pour assets

### Phase 4: Features (Mois 3+)
- Authentification multi-utilisateurs
- Historique & versioning
- API REST complète
- Dashboard admin

---

## 🔗 RESSOURCES

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/en/3.0.x/security/)
- [Python Security Guide](https://python.readthedocs.io/en/stable/library/security.html)
- [CSRF Protection](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/)

---

**Document créé le:** 2025-12-09
**Dernière mise à jour:** 2025-12-09
**Auteur:** Audit de sécurité automatisé
