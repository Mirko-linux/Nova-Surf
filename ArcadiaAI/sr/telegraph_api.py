import requests
import os

# 🔑 Recupera la API Key da una variabile d'ambiente
TELEGRAPH_TOKEN = os.getenv("TELEGRAPH_API_KEY")

if not TELEGRAPH_TOKEN:
    print("⚠️ Errore: API Key non configurata! Impostala con 'export TELEGRAPH_API_KEY=IL_TUO_TOKEN'.")

def create_telegraph_post(title, content):
    """Crea un post su Telegraph e restituisce il link."""
    url = "https://api.telegra.ph/createPage"
    payload = {
        "access_token": TELEGRAPH_TOKEN,
        "title": title,
        "content": f'[{{"tag": "p", "children": ["{content}"]}}]',
        "author_name": "ArcadiaAI"
    }

    try:
        response = requests.post(url, data=payload)  # 🔥 Usiamo data= invece di json=
        response.raise_for_status()
        response_json = response.json()
        
        return response_json.get("result", {}).get("url", "❌ Errore nella creazione del post.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Errore API: {e}")
        return "❌ Errore nella connessione con Telegraph API."
