"""
Routes d'administration
Gestion des logs et accès admin uniquement
"""

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, current_app
from functools import wraps
import os
import json
from datetime import datetime
from app.utils.activity_logger import log_activity

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Décorateur pour vérifier l'authentification admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion admin"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if (username == current_app.config['ADMIN_USERNAME'] and 
            password == current_app.config['ADMIN_PASSWORD']):
            session['is_admin'] = True
            session['admin_username'] = username
            log_activity(f"Connexion admin réussie - Username: {username}", 'info')
            return jsonify({'success': True, 'redirect': url_for('admin.logs')})
        else:
            log_activity(f"Tentative de connexion admin échouée - Username: {username}", 'warning')
            return jsonify({'success': False, 'error': 'Identifiants incorrects'}), 401
    
    return render_template('admin_login.html')


@bp.route('/logout')
def logout():
    """Déconnexion admin"""
    username = session.get('admin_username', 'unknown')
    session.pop('is_admin', None)
    session.pop('admin_username', None)
    log_activity(f"Déconnexion admin - Username: {username}", 'info')
    return redirect(url_for('main.index'))


@bp.route('/logs')
@admin_required
def logs():
    """Page d'affichage des logs d'activité"""
    log_file = current_app.config.get('LOG_FILE', 'logs/app.log')
    
    # Lire les logs
    logs_data = []
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Prendre les 500 dernières lignes et filtrer pour ne garder QUE les logs d'activité
                for line in lines[-500:]:
                    line = line.strip()
                    # Ne garder que les lignes avec le format [user:xxx] [ip:xxx]
                    if line and '[user:' in line and '[ip:' in line:
                        logs_data.append(parse_log_line(line))
            # Inverser pour avoir les plus récents en premier
            logs_data.reverse()
    except Exception as e:
        current_app.logger.error(f"Erreur lecture logs: {str(e)}")
    
    return render_template('admin_logs.html', logs=logs_data)


@bp.route('/api/logs/clear', methods=['POST'])
@admin_required
def clear_logs():
    """Effacer les logs"""
    try:
        log_file = current_app.config.get('LOG_FILE', 'logs/app.log')
        
        if os.path.exists(log_file):
            # Sauvegarder le dernier log de startup
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                startup_lines = [line for line in lines if 'startup' in line.lower()]
            
            # Effacer le fichier
            with open(log_file, 'w', encoding='utf-8') as f:
                if startup_lines:
                    f.write(startup_lines[-1])  # Garder le dernier startup
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO Logs effacés par admin\n")
            
            log_activity("Logs système effacés", 'info')
            return jsonify({'success': True, 'message': 'Logs effacés avec succès'})
        else:
            return jsonify({'success': False, 'error': 'Fichier de logs introuvable'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Erreur effacement logs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/logs')
@admin_required
def api_logs():
    """API pour récupérer les logs en JSON"""
    log_file = current_app.config.get('LOG_FILE', 'logs/app.log')
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level', None)  # INFO, WARNING, ERROR
    user = request.args.get('user', None)
    
    logs_data = []
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-limit*2:]:  # Lire plus pour filtrer
                    line = line.strip()
                    # Ne garder que les lignes avec le format [user:xxx] [ip:xxx]
                    if not line or '[user:' not in line or '[ip:' not in line:
                        continue
                    log_entry = parse_log_line(line)
                    
                    # Filtres
                    if level and log_entry.get('level') != level:
                        continue
                    if user and log_entry.get('user', '').lower() != user.lower():
                        continue
                    
                    logs_data.append(log_entry)
                    
                    if len(logs_data) >= limit:
                        break
            
            logs_data.reverse()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'logs': logs_data, 'count': len(logs_data)})


def parse_log_line(line):
    """Parse une ligne de log et extrait les informations"""
    import re
    try:
        # Format: [YYYY-MM-DD HH:MM:SS] LEVEL [user:username] [ip:xxx.xxx.xxx.xxx] message
        # Regex pour capturer chaque partie
        pattern = r'\[([\d\-: ,]+)\]\s+(\w+)\s+\[user:([^\]]+)\]\s+\[ip:([^\]]+)\]\s+(.+)'
        match = re.match(pattern, line)
        
        if match:
            timestamp = match.group(1).strip()
            level = match.group(2).strip()
            user = match.group(3).strip()
            ip = match.group(4).strip()
            message = match.group(5).strip()
            
            return {
                'timestamp': timestamp,
                'level': level,
                'user': user,
                'ip': ip,
                'message': message,
                'raw': line.strip()
            }
        else:
            # Fallback si le format ne correspond pas
            return {
                'timestamp': '',
                'level': 'INFO',
                'user': 'anonymous',
                'ip': '-',
                'message': line.strip(),
                'raw': line.strip()
            }
    except Exception as e:
        return {
            'timestamp': '',
            'level': 'INFO',
            'user': 'anonymous',
            'ip': '-',
            'message': line.strip(),
            'raw': line.strip()
        }


@bp.route('/stats')
@admin_required
def stats():
    """Statistiques d'utilisation"""
    log_file = current_app.config.get('LOG_FILE', 'logs/app.log')
    
    stats_data = {
        'total_logs': 0,
        'by_level': {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'DEBUG': 0},
        'by_user': {},
        'recent_errors': [],
        'recent_connections': []
    }
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                stats_data['total_logs'] = len(lines)
                
                for line in lines[-1000:]:  # Analyser les 1000 dernières lignes
                    line = line.strip()
                    if not line or line.startswith('*') or line.startswith('WARNING:'):
                        continue
                    log_entry = parse_log_line(line)
                    
                    # Compter par niveau
                    level = log_entry.get('level', 'INFO')
                    if level in stats_data['by_level']:
                        stats_data['by_level'][level] += 1
                    
                    # Compter par utilisateur
                    user = log_entry.get('user', 'anonymous')
                    if user:
                        stats_data['by_user'][user] = stats_data['by_user'].get(user, 0) + 1
                    
                    # Collecter erreurs récentes
                    if level == 'ERROR' and len(stats_data['recent_errors']) < 10:
                        stats_data['recent_errors'].append(log_entry)
                    
                    # Collecter connexions récentes
                    if 'Connexion DHIS2' in log_entry.get('message', '') and len(stats_data['recent_connections']) < 10:
                        stats_data['recent_connections'].append(log_entry)
    except Exception as e:
        current_app.logger.error(f"Erreur calcul stats: {str(e)}")
    
    return render_template('admin_stats.html', stats=stats_data)
