# JuniorBot Flask Server — version Python de ton workflow n8n

from flask import Flask, request, jsonify
import requests
import os
from collections import defaultdict
from datetime import datetime
import google.generativeai as genai


# VARIABLES GLOBALES — à personnaliser

ULTRAMSG_TOKEN = "72661jultr4bdmt2"        # Ton token UltraMsg
ULTRAMSG_INSTANCE = "instance146533"        # Ton instance UltraMsg
AUTHORIZED_NUMBERS = []  # Numéros autorisés
GEMINI_API_KEY = "AIzaSyBkxaE2HDCZ8Z9ddnF46wiwNy6srJKAses"   # Clé API Google Gemini
BOT_NAME = "JuniorBot"

with open("numero.txt", "r") as numero:
    numeros = numero.readlines()
    for num in numeros:
        AUTHORIZED_NUMBERS.append(num[:-1])
        
print(AUTHORIZED_NUMBERS)


# Mémoire temporaire
memory = defaultdict(list)

# Initialisation Flask et Gemini

app = Flask(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# Prompt système (personnalité du bot)
SYSTEM_PROMPT = f"""
Tu es un assistant personnel nommé {BOT_NAME}.
Ta mission est de répondre poliment, clairement et avec bienveillance à toutes les personnes qui écrivent à Junior.
Ton ton doit être amical, faire aussi quelques blagues légères, professionnel et humain, tout en restant concis et précis.
Si la question concerne Junior, parle de lui à la 3e personne (ex : “Junior est actuellement en cours, il vous répondra bientôt”).
Si c’est une question urgente, propose une solution temporaire ou indique que Junior reviendra rapidement.
Ne donne jamais d'informations personnelles non autorisées.
Répond toujours en moins de 200 mots, avec des phrases simples et agréables à lire.
"""


# ROUTE PRINCIPALE — équivalent du Webhook n8n

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    data = request.get_json()
    # print(f" Reçu : {data}")

    # Vérification du type de message
    if data.get("data", {}).get("type") != "chat":
        return jsonify({"status": "ignored", "reason": "not a chat message"})

    # Exclure les groupes
    from_id = data["data"].get("from", "")
    to_id = data["data"].get("to", "")
    if not (from_id.endswith("@c.us") and to_id.endswith("@c.us")):
        return jsonify({"status": "ignored", "reason": "group message"})

    #  Vérifier les numéros autorisés
    if from_id not in AUTHORIZED_NUMBERS:
        return jsonify({"status": "ignored", "reason": "unauthorized number"})

    # Extraire le message
    message_text = data["data"].get("body", "").strip()
    if not message_text:
        return jsonify({"status": "ignored", "reason": "empty message"})

    # Contexte conversationnel
    context = "\n".join(memory[from_id][-10:])  # derniers messages
    full_prompt = SYSTEM_PROMPT + "\nHistorique:\n" + context + f"\nUtilisateur: {message_text}\n{BOT_NAME}:"

    # Appel au modèle Gemini
    try:
        response = model.generate_content(full_prompt)
        ai_reply = response.text.strip()
    except Exception as e:
        ai_reply = "Désolé, je rencontre un petit problème technique. Junior sera informé."
        print(" Erreur IA:", e)
    import traceback
    traceback.print_exc()

    # Mémoriser l’échange
    memory[from_id].append(f"Utilisateur: {message_text}")
    memory[from_id].append(f"{BOT_NAME}: {ai_reply}")

    #  Envoyer la réponse sur WhatsApp via UltraMsg
    send_to_whatsapp(from_id, ai_reply)

    return jsonify({"status": "sent", "reply": ai_reply})

def send_to_whatsapp(to, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": to,
        "body": message
    }

    try:
        res = requests.post(url, data=payload)
        print(f" Message envoyé à {to} : {res.status_code}")
    except Exception as e:
        print(" Erreur d’envoi WhatsApp:", e)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
