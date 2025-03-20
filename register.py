from flask import Blueprint, send_file
import qrcode, io
from globals import waiting_list, registered_queue
from app import socketio

register_bp = Blueprint('register', __name__)

@register_bp.route('/qr')
def generate_qr():
    # Remplacez l'URL par celle de votre serveur (IP publique ou nom de domaine)
    url = "http://147.93.40.205:5000/register"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@register_bp.route('/register', methods=['GET'])
def register():
    if waiting_list:
        number = waiting_list.popleft()
        registered_queue.append(number)
        print("Nouveau participant enregistré : numéro", number)
        socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        return f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="utf-8">
            <title>Numéro attribué</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin: 0;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 80px;
                    margin-bottom: 20px;
                    color: #2c3e50;
                }}
                p {{
                    font-size: 20px;
                    color: #555;
                }}
            </style>
        </head>
        <body>
            <h1>{number}</h1>
            <p>Système de file d'attente développé par Simon Guy, Directeur TI de la SRA</p>
        </body>
        </html>
        """
    else:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="utf-8">
            <title>Aucun numéro disponible</title>
        </head>
        <body style="text-align:center;padding:50px;">
            <h1 style="color:red;">Plus aucun numéro disponible</h1>
        </body>
        </html>
        """, 404
