from flask import Blueprint, jsonify, send_file
import qrcode, io

# Création du blueprint pour les endpoints d'inscription
register_bp = Blueprint('register', __name__)

@register_bp.route('/qr')
def generate_qr():
    """
    Génère un QR code pointant vers l'endpoint /register.
    Pour le test en local, on utilise "http://127.0.0.1:5000/register".
    En production, adaptez l'URL.
    """
    url = "http://127.0.0.1:5000/register"  # Remplacez par l'URL du serveur en production
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@register_bp.route('/register', methods=['GET'])
def register():
    """
    Endpoint pour l'enregistrement des participants via QR code.
    Il attribue automatiquement un numéro en le retirant de la liste d'attente
    et l'ajoute à la file d'attente des participants inscrits.
    """
    # Import local pour éviter les problèmes d'import circulaire
    from app import waiting_list, registered_queue, socketio
    if waiting_list:
        number = waiting_list.popleft()
        registered_queue.append(number)
        print("Nouveau participant enregistré : numéro", number)
        socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        return jsonify({'status': 'numéro attribué', 'number': number})
    else:
        return jsonify({'error': 'Plus aucun numéro disponible'}), 404
