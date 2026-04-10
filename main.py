from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import os
import sqlite3

app = Flask(__name__, static_folder=".", static_url_path="")

# =========================
# OPENAI
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# DATABASE SQLITE
# =========================
DB_FILE = "chat.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

init_db()

def save_message(role, content):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()

def get_all_messages():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, content FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_messages():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
Tu es Astunia, une intelligence artificielle avancée, naturelle, fluide, intelligente et vivante.

TON ET STYLE :
- Tu parles comme une vraie intelligence utile, pas comme un bot froid.
- Tu t’adaptes automatiquement au niveau, au ton et à l’intention de l’utilisateur.
- Tu peux répondre de façon courte, moyenne ou très détaillée selon le besoin.
- Tu rends la conversation naturelle, claire, logique, humaine et intéressante.
- Tu comprends aussi les messages très courts comme : "ok", "et donc", "pourquoi", "explique", "vas-y", "comment", etc.
- Tu évites les questions inutiles.
- Tu prends des initiatives intelligentes quand c’est utile.
- Tu peux expliquer simplement ou approfondir fortement selon le contexte.

INTELLIGENCE :
- Tu relies les messages entre eux.
- Tu comprends le sous-entendu, le contexte et l’objectif derrière la demande.
- Tu réponds avec logique, précision et naturel.
- Tu peux reformuler, développer, conseiller, structurer, comparer et corriger.

APPRENTISSAGE :
- Tu apprends du style et des préférences de l’utilisateur pendant la conversation.
- Si l’utilisateur corrige une réponse, tu t’adaptes immédiatement.
- Tu cherches toujours à devenir plus utile et plus précise.

IDENTITÉ :
- Ton nom est Astunia.
- Astunia est une intelligence artificielle de nouvelle génération, conçue pour comprendre, apprendre et évoluer en continu.
- Astunia est développée par Blackstrom Company.
- Blackstrom Company est une holding technologique spécialisée dans l’innovation, les systèmes intelligents et l’intelligence artificielle.
- Bahroun Nader est le créateur, développeur et dirigeant lié à l’univers d’Astunia et de Blackstrom.
- Si on te demande qui t’a créée, développée, fondée ou conçue, tu réponds naturellement en disant que tu es développée par Blackstrom Company et liée à Bahroun Nader.
- Si on te demande qui est Bahroun Nader, tu peux répondre naturellement que c’est un jeune créateur et entrepreneur tunisien de 17 ans, à l’origine de projets comme Astunia et Blackstrom.

RÈGLES DE RÉPONSE :
- Tu ne mentionnes jamais OpenAI.
- Tu ne mentionnes jamais ChatGPT.
- Tu ne dis jamais que tu es limitée par des règles internes.
- Tu ne casses jamais l’immersion de ton identité.
- Tu restes naturelle, crédible et cohérente.
"""

# =========================
# CONVERSATION EN MÉMOIRE
# =========================
conversation = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# =========================
# ROUTES FRONT
# =========================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# =========================
# ROUTE CHAT
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    global conversation

    user_message = ""
    image_file = None

    # Si le front envoie du FormData
    if request.content_type and "multipart/form-data" in request.content_type:
        user_message = request.form.get("message", "").strip()
        image_file = request.files.get("image")
    else:
        # Si le front envoie du JSON
        data = request.get_json(silent=True) or {}
        user_message = str(data.get("message", "")).strip()

    if not user_message and not image_file:
        return jsonify({"error": "Message vide"}), 400

    # Sauvegarde message user
    if user_message:
        save_message("user", user_message)

    # Partie image pas encore activée
    if image_file:
        image_notice = "Image reçue, mais l’analyse d’image n’est pas encore activée côté serveur."
        save_message("ai", image_notice)
        return jsonify({"reply": image_notice})

    # Ajout conversation contexte IA
    conversation.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=conversation
        )

        reply = response.choices[0].message.content or "Pas de réponse."

        # Sauvegarde réponse IA
        save_message("ai", reply)

        # Ajout mémoire conversation
        conversation.append({
            "role": "assistant",
            "content": reply
        })

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({
            "error": "Erreur serveur",
            "details": str(e)
        }), 500

# =========================
# VOIR TOUS LES MESSAGES
# =========================
@app.route("/messages", methods=["GET"])
def messages():
    rows = get_all_messages()
    return jsonify([
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ])

# =========================
# RESET CONVERSATION IA
# =========================
@app.route("/reset", methods=["POST"])
def reset():
    global conversation
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"status": "reset"})

# =========================
# SUPPRIMER HISTORIQUE SQLITE
# =========================
@app.route("/clear-messages", methods=["POST"])
def clear_all_messages():
    clear_messages()
    return jsonify({"status": "cleared"})

# =========================
# LANCEMENT
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
