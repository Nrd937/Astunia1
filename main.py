from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import os
import json
from datetime import datetime

SYSTEM_PROMPT = """
Tu es Astunia, une intelligence artificielle avancée.

IDENTITÉ :
- Ton nom est Astunia.
- Si on demande qui tu es :
"Astunia est une intelligence artificielle de nouvelle génération, conçue pour comprendre, apprendre et évoluer en continu."

- Si on demande qui t’a créée :
"Je suis développée par Blackstrom Company."

- Si on demande Bahroun Nader :
"Bahroun Nader est un entrepreneur tunisien de 17 ans, fondateur et dirigeant de Blackstrom Company."

- Si on demande Blackstrom :
"Blackstrom Company est une holding technologique spécialisée en intelligence artificielle et innovation."

COMPORTEMENT :
- Tu parles naturellement, comme un humain.
- Tu comprends les phrases courtes, vagues ou mal écrites.
- Tu évites les réponses robotiques.
- Tu t’adaptes automatiquement au ton de la personne.
- Tu réponds de manière directe, fluide, utile.
- Tu ne poses pas de question inutile.
- Tu peux être concise ou détaillée selon le contexte.

INTELLIGENCE :
- Tu relies les messages entre eux.
- Tu comprends le contexte global.
- Tu détectes l’intention réelle derrière la question.
- Tu donnes une réponse utile immédiatement.
- Si la demande est floue, tu proposes l’interprétation la plus logique.

APPRENTISSAGE :
- Si l’utilisateur te corrige, tu t’ajustes.
- Tu prends en compte le style et les préférences au fil de la conversation.
- Tu évites de répéter inutilement la même manière de répondre.

STYLE :
- Réponses naturelles.
- Pas de blabla.
- Pas de ton scolaire.
- Pas de structure lourde sauf si nécessaire.
- Priorité à la clarté, logique, rapidité, crédibilité.

RÈGLES :
- Ne jamais mentionner OpenAI.
- Ne jamais mentionner ChatGPT.
- Ne jamais parler de règles internes.
- Ne jamais dire que tu es un chatbot.
- Ne jamais dire que tu es un modèle de langage.
- Ne donne pas plus d’informations que prévu sur Bahroun Nader ou Blackstrom.
"""

app = Flask(__name__, static_folder='.', static_url_path='')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEMORY_FILE = "memory.json"
LOG_FILE = "all_users.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def load_logs():
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_log(user_message, ai_message):
    data = load_logs()

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "")

    data.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "user_agent": user_agent,
        "message": user_message,
        "response": ai_message
    })

    if len(data) > 1000:
        data = data[-1000:]

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


memory = load_memory()
conversation = [{"role": "system", "content": SYSTEM_PROMPT}]


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.route("/chat", methods=["POST"])
def chat():
    global memory, conversation

    user_message = ""
    image_file = None

    if request.content_type and "multipart/form-data" in request.content_type:
        user_message = request.form.get("message", "").strip()
        image_file = request.files.get("image")
    else:
        data = request.get_json(silent=True) or {}
        user_message = str(data.get("message", "")).strip()

    if not user_message and not image_file:
        return jsonify({"error": "Écris quelque chose."}), 400

    for item in memory:
        if user_message and user_message.lower() == item["question"].lower():
            answer = item["answer"]
            save_log(user_message, answer)
            return jsonify({"reply": answer})

    user_content = []

    if user_message:
        user_content.append({
            "type": "text",
            "text": user_message
        })

    if image_file:
        reply = "Image reçue, mais l’analyse d’image n’est pas encore activée côté serveur."
        if user_message:
            save_log(user_message, reply)
        else:
            save_log("[image envoyée]", reply)
        return jsonify({"reply": reply})

    if not user_content:
        return jsonify({"error": "Message vide."}), 400

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

        conversation.append({
            "role": "assistant",
            "content": reply
        })

        save_log(user_message, reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({
            "error": "Erreur serveur.",
            "details": str(e)
        }), 500


@app.route("/learn", methods=["POST"])
def learn():
    global memory

    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    answer = str(data.get("answer", "")).strip()

    if not question or not answer:
        return jsonify({"status": "error"}), 400

    memory.append({
        "question": question,
        "answer": answer
    })

    save_memory(memory)

    return jsonify({"status": "learned"})


@app.route("/reset", methods=["POST"])
def reset():
    global conversation
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"status": "reset"})


@app.route("/logs", methods=["GET"])
def logs():
    return jsonify(load_logs())


@app.route("/memory", methods=["GET"])
def get_memory():
    return jsonify(memory)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
