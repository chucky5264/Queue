#!/usr/bin/env python
import eventlet
eventlet.monkey_patch()  # À appeler avant tout autre import !

from flask import Flask, request, jsonify, send_file, Blueprint, session
from flask_socketio import SocketIO
from collections import deque, OrderedDict
import qrcode, io, uuid

# Génère un identifiant unique pour cette exécution de l'application.
app_run_id = str(uuid.uuid4())

# Configure Flask (nous ne faisons plus référence aux images, donc la partie static reste inchangée)
app = Flask(__name__, static_folder='sstatic', static_url_path='/static')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Variables globales partagées
waiting_list = deque(range(1, 3001))      # Liste d'attente des numéros disponibles
registered_queue = deque()               # File d'attente des participants inscrits
active_counters = OrderedDict()          # Dernier numéro appelé par chaque comptoir

# --- Blueprint pour l'enregistrement ---
register_bp = Blueprint('register', __name__)

@register_bp.route('/qr')
def generate_qr():
    """
    Génère un QR code pointant vers l'endpoint /register.
    """
    url = "http://147.93.40.205:5000/register"  # Adaptez l'URL selon votre environnement
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@register_bp.route('/register', methods=['GET'])
def register():
    """
    Endpoint d'enregistrement par QR code.
    Vérifie si la session contient déjà un numéro correspondant à la version actuelle de l'application.
    Sinon, un nouveau numéro est attribué et ajouté à la file d'attente.
    """
    if session.get('app_run_id') == app_run_id and 'assigned_number' in session:
        number = session['assigned_number']
    else:
        if waiting_list:
            number = waiting_list.popleft()
            registered_queue.append(number)
            session['assigned_number'] = number
            session['app_run_id'] = app_run_id
            print("Nouveau participant enregistré : numéro", number)
            socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        else:
            return """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
              <meta charset="utf-8">
              <title>Aucun numéro disponible</title>
            </head>
            <body style="text-align:center; padding:50px;">
              <h1 style="color:red;">Plus aucun numéro disponible</h1>
            </body>
            </html>
            """, 404

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
          background-color: #ffffff;
        }}
        h1 {{
          font-size: 150px;
          margin-bottom: 20px;
          color: #2c3e50;
          margin-top: 50px;
        }}
        p {{
          font-size: 30px;
          color: #555;
        }}
      </style>
    </head>
    <body>
      <h1>{number}</h1>
      <p>Numéro attribué via enregistrement QR</p>
    </body>
    </html>
    """

@register_bp.route('/manual', methods=['GET', 'POST'])
def manual_register():
    """
    Page d'assignation manuelle d'un numéro.
    Lorsqu'un utilisateur clique sur le bouton, un nouveau numéro est attribué (et ajouté à la file)
    et le numéro attribué est affiché.
    """
    if request.method == 'POST':
        if waiting_list:
            number = waiting_list.popleft()
            registered_queue.append(number)
            socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        else:
            return """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
              <meta charset="utf-8">
              <title>Aucun numéro disponible</title>
            </head>
            <body style="text-align:center; padding:50px;">
              <h1 style="color:red;">Plus aucun numéro disponible</h1>
            </body>
            </html>
            """, 404

        return f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="utf-8">
            <title>Assignation Manuelle</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin: 0;
                    padding: 50px;
                    background-color: #ffffff;
                }}
                h1 {{
                    font-size: 150px;
                    color: #2c3e50;
                    margin-bottom: 20px;
                }}
                p {{
                    font-size: 30px;
                    color: #555;
                }}
                a {{
                    display: block;
                    margin-top: 20px;
                    text-decoration: none;
                    color: #2980b9;
                    font-size: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>{number}</h1>
            <p>Numéro attribué manuellement</p>
            <a href="/manual">Attribuer un autre numéro</a>
            <a href="/">Retour à l'accueil</a>
        </body>
        </html>
        """
    else:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="utf-8">
            <title>Assignation Manuelle</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    margin: 0; 
                    padding: 50px; 
                    background-color: #ffffff;
                }
                h1 { 
                    font-size: 2em; 
                    color: #2c3e50; 
                    margin-bottom: 20px; 
                }
                button { 
                    font-size: 1.5em; 
                    padding: 10px 20px; 
                    background: #2980b9; 
                    color: #fff; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer; 
                }
                button:hover { 
                    background: #1f6390; 
                }
                a { 
                    display: block; 
                    margin-top: 20px; 
                    text-decoration: none; 
                    color: #2980b9; 
                    font-size: 20px; 
                }
            </style>
        </head>
        <body>
            <h1>Assignation Manuelle de Numéro</h1>
            <form method="post">
                <button type="submit">Attribuer un numéro</button>
            </form>
            <a href="/">Retour à l'accueil</a>
        </body>
        </html>
        """

# Enregistre le blueprint dans l'application
app.register_blueprint(register_bp)

# --- Routes principales de l'application ---

@app.route('/')
def home():
    """
    Page d'accueil sans images, avec des liens vers l'enregistrement par QR et l'assignation manuelle.
    """
    liens = "".join(f'<li><a href="/counter/{i}">Comptoir {i}</a></li>' for i in range(1, 61))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Système de File d'Attente</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 20px;
          background-color: #f9f9f9;
          text-align: center;
        }}
        h1 {{
          background: #2c3e50;
          color: #ecf0f1;
          padding: 10px;
          margin: 0;
        }}
        .container {{
          max-width: 800px;
          margin: 80px auto;
          background: #fff;
          padding: 20px;
          box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        ul {{
          list-style-type: none;
          padding: 0;
        }}
        li {{
          margin-bottom: 10px;
          font-size: 16px;
        }}
        a {{
          text-decoration: none;
          color: #2980b9;
        }}
        a:hover {{
          text-decoration: underline;
        }}
      </style>
    </head>
    <body>
      <h1>Système de File d'Attente</h1>
      <div class="container">
        <p>Bienvenue ! Ce système vous permet de gérer une file d'attente et d'appeler le prochain numéro depuis n'importe quel comptoir.</p>
        <p><a href="/qr">Afficher le QR code pour s'enregistrer</a></p>
        <p><a href="/manual">Attribuer un numéro manuellement</a></p>
        <h2>Liste des Comptoirs</h2>
        <ul>
          {liens}
        </ul>
      </div>
    </body>
    </html>
    """

@app.route('/counter/<int:counter_id>', methods=['GET'])
def counter_page(counter_id):
    """
    Page dédiée à un comptoir sans images.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Comptoir {counter_id}</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 20px;
          background-color: #f9f9f9;
          text-align: center;
        }}
        h1 {{
          background: #2c3e50;
          color: #ecf0f1;
          padding: 10px;
          margin: 0;
        }}
        .container {{
          max-width: 600px;
          margin: 80px auto;
          background: #fff;
          padding: 20px;
          box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        #callNextBtn {{
          padding: 10px 20px;
          background: #2980b9;
          color: #fff;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
        }}
        #callNextBtn:hover {{
          background: #1f6390;
        }}
        #result {{
          margin-top: 20px;
          font-size: 18px;
          color: #333;
        }}
        a {{
          text-decoration: none;
          color: #2980b9;
        }}
        a:hover {{
          text-decoration: underline;
        }}
      </style>
    </head>
    <body>
      <h1>Comptoir {counter_id}</h1>
      <div class="container">
        <p>Cliquez sur le bouton ci-dessous pour appeler le prochain participant inscrit.</p>
        <button id="callNextBtn">Appeler le prochain numéro</button>
        <div id="result"></div>
        <p><a href="/">Retour à l'accueil</a></p>
      </div>
      <script>
        document.getElementById('callNextBtn').addEventListener('click', function() {{
          fetch('/next', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{counter: 'Comptoir {counter_id}'}})
          }})
          .then(response => response.json())
          .then(data => {{
            if (data.error) {{
              document.getElementById('result').innerText = data.error;
            }} else {{
              document.getElementById('result').innerText = 'Numéro appelé pour ' + data.counter + ' : ' + data.number;
            }}
          }})
          .catch(err => console.error(err));
        }});
      </script>
    </body>
    </html>
    """

@app.route('/next', methods=['POST'])
def next_client():
    """
    Endpoint appelé par un comptoir pour récupérer le prochain numéro.
    """
    print("File actuelle:", list(registered_queue))
    data = request.get_json()
    counter = data.get('counter')
    if not counter:
        return jsonify({'error': "L'identifiant du comptoir est requis"}), 400

    if registered_queue:
        next_number = registered_queue.popleft()
        active_counters[counter] = next_number
        active_counters.move_to_end(counter, last=True)
        print("Appel du numéro pour", counter, ":", next_number)
        socketio.emit('update', {'active_counters': list(active_counters.items())})
        socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        return jsonify({'status': 'appelé', 'counter': counter, 'number': next_number})
    else:
        return jsonify({'error': 'Aucun participant en attente'}), 404

@app.route('/display', methods=['GET'])
def display():
    """
    Page d'affichage en direct des comptoirs et de la file d'attente avec un style moderne.
    """
    items = list(reversed(active_counters.items()))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Affichage en Direct des Comptoirs</title>
      <style>
        body {{
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background-color: #f0f2f5;
          margin: 0;
          padding: 20px;
        }}
        .header {{
          background: #2c3e50;
          color: #ecf0f1;
          padding: 20px;
          text-align: center;
          font-size: 2em;
        }}
        .container {{
          max-width: 1000px;
          margin: 40px auto;
          background: #ffffff;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          border-radius: 8px;
        }}
        h2 {{
          color: #2c3e50;
          margin-bottom: 20px;
        }}
        .counters-list {{
          display: flex;
          flex-wrap: wrap;
          justify-content: space-around;
        }}
        .counter-card {{
          background: #ecf0f1;
          border-radius: 8px;
          padding: 20px;
          margin: 10px;
          flex: 1 0 200px;
          max-width: 300px;
          text-align: center;
        }}
        .counter-card h3 {{
          margin: 0;
          font-size: 1.5em;
          color: #34495e;
        }}
        .counter-card p {{
          font-size: 1.2em;
          color: #2c3e50;
          margin: 10px 0 0;
        }}
        .queue-section {{
          margin-top: 40px;
        }}
        .queue-section ul {{
          list-style: none;
          padding: 0;
        }}
        .queue-section li {{
          background: #ecf0f1;
          margin: 5px 0;
          padding: 10px;
          border-radius: 4px;
          font-size: 1.1em;
          color: #2c3e50;
        }}
        a {{
          text-decoration: none;
          color: #2980b9;
        }}
        a:hover {{
          text-decoration: underline;
        }}
      </style>
    </head>
    <body>
      <div class="header">
        Affichage en Direct des Comptoirs
      </div>
      <div class="container">
        <h2>Derniers numéros appelés</h2>
        <div class="counters-list">
          {"".join(f'''
          <div class="counter-card">
            <h3>{counter}</h3>
            <p>Numéro {number}</p>
          </div>
          ''' for counter, number in items)}
        </div>
        <div class="queue-section">
          <h2>File d'attente des participants</h2>
          {"".join(f"<li>Numéro {number}</li>" for number in list(registered_queue)) if registered_queue else "<p>Aucun participant en attente.</p>"}
        </div>
        <p style="text-align:center; margin-top: 20px;"><a href="/">Retour à l'accueil</a></p>
      </div>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.min.js"></script>
      <script>
        var socket = io();
        socket.on('connect', function() {{
          console.log("Connecté à Socket.IO !");
        }});
        socket.on('update', function(data) {{
          console.log("Événement update reçu :", data);
          location.reload();
        }});
        socket.on('update_queue', function(data) {{
          console.log("Mise à jour de la file d'attente :", data);
          location.reload();
        }});
      </script>
    </body>
    </html>
    """

@app.route('/test-emit')
def test_emit():
    socketio.emit('update', {'active_counters': list(active_counters.items())})
    socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
    return "Événement de test émis !"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
