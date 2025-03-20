from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import eventlet
eventlet.monkey_patch()

from globals import waiting_list, registered_queue, active_counters

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Importer et enregistrer le blueprint d'inscription
from register import register_bp
app.register_blueprint(register_bp)

@app.route('/')
def home():
    # Générer dynamiquement des liens pour 60 comptoirs
    liens = "".join(f'<li><a href="/counter/{i}">Comptoir {i}</a></li>' for i in range(1, 61))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accueil - Système de File d'Attente</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f9f9f9;
            }}
            h1 {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
            }}
            .container {{
                max-width: 800px;
                margin: 20px auto;
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
            <p><a href="/display">Voir l'affichage en direct des comptoirs</a></p>
            <p><a href="/qr">Afficher le QR code pour s'enregistrer</a></p>
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
                background: #f9f9f9;
            }}
            h1 {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
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
        # Émettre l'événement update pour actualiser l'affichage des comptoirs
        socketio.emit('update', {'active_counters': list(active_counters.items())})
        # Mettre à jour la file d'attente des participants sur l'affichage
        socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        return jsonify({'status': 'appelé', 'counter': counter, 'number': next_number})
    else:
        return jsonify({'error': 'Aucun participant en attente'}), 404

@app.route('/display', methods=['GET'])
def display():
    items = list(reversed(active_counters.items()))
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Affichage en Direct des Comptoirs</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f9f9f9;
            }
            h1 {
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
            }
            .container {
                max-width: 800px;
                margin: 20px auto;
                background: #fff;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                margin: 10px 0;
                font-size: 18px;
            }
            .empty {
                color: #888;
                font-style: italic;
            }
            a {
                text-decoration: none;
                color: #2980b9;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
        <!-- Charger la bibliothèque client Socket.IO -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.min.js"></script>
    </head>
    <body>
        <h1>Affichage en Direct des Comptoirs</h1>
        <div class="container">
            <div id="countersList">
    """
    if items:
        html += "<ul>"
        for counter, number in items:
            html += f"<li><strong>{counter}</strong> : Numéro {number}</li>"
        html += "</ul>"
    else:
        html += "<p class='empty'>Aucun numéro appelé pour le moment.</p>"
    
    html += """
            </div>
            <h2>File d'attente des participants</h2>
            <div id="queueList"></div>
            <p><a href="/">Retour à l'accueil</a></p>
        </div>
        <script>
            var socket = io();
            socket.on('connect', function() {
                console.log("Connecté à Socket.IO !");
            });
            socket.on('update', function(data) {
                console.log("Événement update reçu :", data);
                var items = data.active_counters.slice().reverse();
                var html = "<ul>";
                items.forEach(function(item) {
                    html += "<li><strong>" + item[0] + "</strong> : Numéro " + item[1] + "</li>";
                });
                html += "</ul>";
                document.getElementById('countersList').innerHTML = html;
            });
            socket.on('update_queue', function(data) {
                console.log("Mise à jour de la file d'attente :", data);
                var queue = data.registered_queue;
                var html = "";
                if(queue.length > 0) {{
                    html = "<ul>";
                    queue.forEach(function(number) {{
                        html += "<li>Numéro " + number + "</li>";
                    }});
                    html += "</ul>";
                }} else {{
                    html = "<p class='empty'>Aucun participant en attente.</p>";
                }}
                document.getElementById('queueList').innerHTML = html;
            });
        </script>
    </body>
    </html>
    """
    return html

@app.route('/test-emit')
def test_emit():
    socketio.emit('update', {'active_counters': list(active_counters.items())})
    socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
    return "Événement de test émis !"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
