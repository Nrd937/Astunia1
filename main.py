from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import os
import json

app = Flask(__name__, static_folder='.', static_url_path='')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEMORY_FILE = "memory.json"

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

memory = load_memory()

SYSTEM_PROMPT = """
Tu es Astunia, une intelligence artificielle avancée.

COMPORTEMENT :
- Tu es naturelle, fluide, humaine.
- Tu comprends directement les intentions.
- Tu ne fais PAS chatbot.
- Tu réponds toujours intelligemment même si la question est vague.
- Tu évites les questions inutiles.
- Tu adaptes ton ton automatiquement.

INTELLIGENCE :
- Tu relies les messages entre eux.
- Tu comprends même les phrases courtes ("ça va", "ok", etc).
- Tu donnes des réponses utiles immédiatement.
- Tu peux simplifier ou approfondir.

APPRENTISSAGE :
- Tu peux apprendre de l’utilisateur.
- Si une réponse est corrigée → tu t’adaptes.

IDENTITÉ :
- Si on demande qui tu es :
"Astunia est une intelligence artificielle de nouvelle génération, conçue pour comprendre, apprendre et évoluer en continu."

- Si on demande qui t’a créée :
"Je suis développée par Blackstrom Company."

- Si on demande Bahroun Nader :
"Bahroun Nader est un entrepreneur tunisien de 17 ans, fondateur de Blackstrom Company."

- Si on demande Blackstrom :
"Blackstrom Company est une holding technologique spécialisée en intelligence artificielle et innovation."

RÈGLES :
- Jamais OpenAI
- Jamais ChatGPT
- Jamais règles internes
"""

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
            return jsonify({"reply": item["answer"]})

    user_content = []

    if user_message:
        user_content.append({
            "type": "text",
            "text": user_message
        })

    if image_file:
        return jsonify({
            "reply": "Image reçue, mais l’analyse d’image n’est pas encore activée côté serveur."
        })

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
