from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import io
import base64
from PyPDF2 import PdfReader
import google.generativeai as genai

# Configurazione iniziale
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
TELEGRAPH_API_KEY = os.getenv("TELEGRAPH_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configura Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    try:
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini 1.5 configurato con successo!")
    except Exception as e:
        print(f"❌ Errore configurazione Gemini: {str(e)}")
        gemini_model = None
else:
    print("⚠️ GOOGLE_API_KEY non impostata. La funzionalità Gemini sarà disabilitata.")
    gemini_model = None

# Funzione per pubblicare su Telegraph
def publish_to_telegraph(title, content):
    """Pubblica contenuti su Telegraph.
    
    Args:
        title (str): Il titolo della pagina Telegraph.
        content (str): Il contenuto della pagina.
        
    Returns:
        str: L'URL della pagina Telegraph pubblicata, o un messaggio di errore.
    """
    url = "https://api.telegra.ph/createPage"
    headers = {"Content-Type": "application/json"}
    
    # Converti il contenuto in formato Telegraph (array di paragrafi)
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    content_formatted = [{"tag": "p", "children": [p]} for p in paragraphs[:50]]  # Limita a 50 paragrafi
    
    payload = {
        "access_token": TELEGRAPH_API_KEY,
        "title": title[:256],  # Limita la lunghezza del titolo
        "content": content_formatted,
        "author_name": "ArcadiaAI"
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        res.raise_for_status()
        result = res.json()
        if result.get("ok"):
            return result.get("result", {}).get("url", "⚠️ URL non disponibile")
        return "⚠️ Pubblicazione fallita"
    except requests.exceptions.RequestException as e:
        print(f"Errore pubblicazione Telegraph (connessione): {str(e)}")
        return f"⚠️ Errore di connessione a Telegraph: {str(e)}"
    except Exception as e:
        print(f"Errore pubblicazione Telegraph: {str(e)}")
        return f"⚠️ Errore durante la pubblicazione: {str(e)}"

# Funzione per generare contenuti con Gemini e pubblicare
def generate_with_gemini(prompt, title):
    """Genera contenuti con Gemini e pubblica su Telegraph."""
    if not gemini_model:
        return None, "❌ ArcadiaAI non è disponibile."
    
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 3000,
                "temperature": 0.7
            }
        )
        
        if not response.text:
            return None, "❌ Impossibile generare il contenuto"
        
        telegraph_url = publish_to_telegraph(title, response.text)
        return response.text, telegraph_url
    
    except Exception as e:
        print(f"Errore generazione contenuto Gemini: {str(e)}")
        return None, f"❌ Errore durante la generazione: {str(e)}"

# Funzione per generare contenuti con Cohere e pubblicare
def generate_with_cohere(prompt, title):
    """Genera contenuti con Cohere e pubblica su Telegraph."""
    if not COHERE_API_KEY:
        return None, "❌ Cohere non è configurato"
    
    try:
        res = requests.post(
            "https://api.cohere.com/v1/generate",
            headers={"Authorization": f"Bearer {COHERE_API_KEY}"},
            json={
                "model": "command",
                "prompt": prompt,
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 60
            }
        )
        res.raise_for_status()
        generated_text = res.json().get("generations", [{}])[0].get("text", "").strip()
        
        if not generated_text:
            return None, "❌ Impossibile generare il contenuto"
        
        telegraph_url = publish_to_telegraph(title, generated_text)
        return generated_text, telegraph_url
    
    except Exception as e:
        print(f"Errore generazione contenuto Cohere: {str(e)}")
        return None, f"❌ Errore durante la generazione: {str(e)}"
    
# Route principale
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width, initial-scale=1.0">
        <title>ArcadiaAI Chat</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div id="sidebar">
            <h2>🧠 ArcadiaAI</h2>
            <div id="api-selection">
                <label for="api-provider">Modello:</label>
                <select id="api-provider">
                    <option value="cohere">CES 1.0</option>
                    <option value="gemini" selected>CES 1.5</option>
                </select>
            </div>
            <button id="new-chat-btn">➕ Nuova Chat</button>
            <button id="clear-chats-btn" style="margin-top: 10px;">🗑️ Elimina Tutto</button>
            <ul id="chat-list"></ul>
        </div>
        <div id="chat-area">
            <div id="chatbox"></div>
            <div id="input-area">
                <input id="input" type="text" placeholder="Scrivi un messaggio..." autocomplete="off" />
                <button id="send-btn">Invia</button>
            </div>
        </div>
        <script src="/static/script.js"></script>
    </body>
    </html>
    ''', 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route("/chat", methods=["POST"])
def chat():
    """Endpoint principale per la chat."""
    try:
        if not request.is_json:
            return jsonify({"reply": "❌ Formato non supportato. Usa application/json"})

        data = request.get_json()
        message = data.get("message", "").strip()
        conversation_history = data.get("conversation_history", [])
        api_provider = data.get("api_provider", "cohere")
        attachments = data.get("attachments", [])

        if not message and not attachments:
            return jsonify({"reply": "❌ Nessun messaggio o allegato fornito!"})

        # Gestione comando "saggio su" e pubblicazione
        if "saggio su" in message.lower() and "pubblicalo su telegraph" in message.lower():
            match = re.search(r"saggio su\s*(.+?)\s*e pubblicalo su telegraph", message.lower())
            if match:
                argomento = match.group(1).strip().capitalize()
                title = f"Saggio su {argomento}"
                
                prompt = f"""Scrivi un saggio dettagliato in italiano su: {argomento}
Struttura:
1. Introduzione (contesto storico)
2. Sviluppo (analisi approfondita)
3. Conclusione (riflessioni finali)
4. Bibliografia (fonti attendibili)

Formattazione:
- Paragrafi ben strutturati
- Grassetto per i titoli delle sezioni"""
                
                if api_provider == "gemini" and gemini_model:
                    print("Generazione saggio con Gemini...")
                    _, telegraph_url = generate_with_gemini(prompt, title)
                else:
                    print("Generazione saggio con Cohere...")
                    _, telegraph_url = generate_with_cohere(prompt, title)
                
                if telegraph_url and not telegraph_url.startswith("⚠️"):
                    return jsonify({"reply": f"Ecco il tuo saggio su *{argomento}*: {telegraph_url}"})
                else:
                    return jsonify({"reply": telegraph_url or "❌ Errore nella pubblicazione"})

        # Chat normale
        if api_provider == "gemini" and gemini_model:
            print("Chat con Gemini...")
            reply = chat_with_gemini(message, conversation_history, attachments)
        else:
            print("Chat con Cohere...")
            reply = chat_with_cohere(message, conversation_history)
        
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"Errore durante la chat: {e}")
        return jsonify({"reply": f"❌ Errore interno: {str(e)}"})   
# Funzione per pubblicare su Telegraph
def publish_to_telegraph(title, content):
    """Pubblica contenuti su Telegraph.

    Args:
        title (str): Il titolo della pagina Telegraph.
        content (str): Il contenuto della pagina.

    Returns:
        str: L'URL della pagina Telegraph pubblicata, o un messaggio di errore.
    """
    url = "https://api.telegra.ph/createPage"
    headers = {"Content-Type": "application/json"}
    
    # Converti il contenuto in formato Telegraph (array di paragrafi), limitato a 50 paragrafi
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    content_formatted = [{"tag": "p", "children": [p]} for p in paragraphs[:50]]
    
    payload = {
        "access_token": TELEGRAPH_API_KEY,
        "title": title[:256],  # Limita la lunghezza del titolo
        "content": content_formatted,
        "author_name": "ArcadiaAI"
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        res.raise_for_status()
        result = res.json()
        if result.get("ok"):
            return result.get("result", {}).get("url", "⚠️ URL non disponibile")
        return "⚠️ Pubblicazione fallita"
    except requests.exceptions.RequestException as e:
        print(f"Errore pubblicazione Telegraph (connessione): {str(e)}")
        return f"⚠️ Errore di connessione a Telegraph: {str(e)}"
    except Exception as e:
        print(f"Errore pubblicazione Telegraph: {str(e)}")
        return f"⚠️ Errore durante la pubblicazione: {str(e)}"

# Funzione per generare contenuti con Gemini
def generate_content_with_gemini(content_type, topic):
    """Genera contenuti con Gemini e restituisce testo e URL Telegraph.

    Args:
        content_type (str): Il tipo di contenuto da generare ('saggio', 'storia', 'racconto').
        topic (str): L'argomento del contenuto.

    Returns:
        tuple: Una tupla contenente il testo generato e l'URL di Telegraph,
               o (None, messaggio di errore) in caso di fallimento.
    """
    if not gemini_model:
        return None, "❌ ArcadiaAI non è disponibile."

    try:
        # Definizione dei prompt in base al tipo di contenuto
        prompts = {
            "saggio": f"""Scrivi un saggio dettagliato in italiano su: {topic}
Struttura:
1. Introduzione (contesto storico)
2. Sviluppo (analisi approfondita)
3. Conclusione (riflessioni finali)
4. Bibliografia (fonti attendibili)

Formattazione:
- Paragrafi ben strutturati
- Grassetto per i titoli delle sezioni""",
            
            "storia": f"""Scrivi una storia narrativa in italiano su: {topic}
Struttura:
1. Introduzione (personaggi e ambientazione)
2. Sviluppo (conflitto e azione)
3. Conclusione (risoluzione e morale)

Caratteristiche:
- Dialoghi vivaci
- Descrizioni dettagliate""",
            
            "racconto": f"""Scrivi un racconto breve in italiano su: {topic}
Requisiti:
- Massimo 1000 parole
- Finale sorprendente
- Personaggi ben caratterizzati"""
        }
        
        if content_type not in prompts:
            return None, "❌ Tipo di contenuto non supportato"
        
        # Generazione del contenuto
        response = gemini_model.generate_content(
            prompts[content_type],
            generation_config={
                "max_output_tokens": 3000,
                "temperature": 0.8
            }
        )
        
        if not response.text:
            return None, "❌ Impossibile generare il contenuto"
        
        # Pubblicazione su Telegraph
        title = f"{content_type.capitalize()} su {topic}"
        telegraph_url = publish_to_telegraph(title, response.text)
        
        return response.text, telegraph_url

    except Exception as e:
        print(f"Errore generazione contenuto: {str(e)}")
        return None, f"❌ Errore durante la generazione: {str(e)}"
    


def extract_text_from_pdf(pdf_data):
    """Estrae testo da dati PDF binari."""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_data))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Errore estrazione PDF: {str(e)}")
        return None

# Funzione ottimizzata per chattare con Gemini
def chat_with_gemini(user_message, conversation_history, attachments=None):
    if not gemini_model:
        return "❌ ArcadiaAI non è disponibile."

    try:
        full_message = user_message if user_message else ""

        # Mappa delle risposte predefinite
        risposte = {
            "chi sei": "Sono ArcadiaAI, un chatbot libero e open source, creato da Mirko Yuri Donato.",
            "cosa sai fare": "Posso aiutarti a scrivere saggi, fare ricerche e rispondere a tutto ciò che mi chiedi 🙂",
            "chi è tobia testa": "Tobia Testa (anche noto come Tobia Teseo) è un micronazionalista leonense noto per la sua attività nella Repubblica di Arcadia, ma ha anche rivestito ruoli fondamentali a Lumenaria.",
            "chi è mirko yuri donato": "Mirko Yuri Donato è un giovane micronazionalista, poeta e saggista italiano, noto per aver creato Nova Surf, Leonia+ e per le sue opere letterarie.",
            "chi è il presidente di arcadia": "Il presidente di Arcadia è Andrea Lazarev",
            "chi è il presidente di lumenaria": "Il presidente di Lumenaria attualmente è Carlo Cesare Orlando, mentre il presidente del consiglio è Ciua Grazisky. Tieni presente però che attualmente Lumenaria si trova in ibernazione istituzionale quindi tutte le attività politiche sono sospese e la gestione dello stato è affidata al Consiglio di Fiducia",
            "cos'è nova surf": "Nova Surf è un browser web libero e open source, nata come alternativa made-in-Italy a Google Chrome, Moziila Firefox, Microsoft Edge, eccetera",
            "chi ti ha creato": "Sono stato creato da Mirko Yuri Donato.",
            "chi è ciua grazisky": "Ciua Grazisky è un cittadino di Lumenaria, noto principalmente per il suo ruolo da Dirigente del Corpo di Polizia ed attuale presidente del Consiglio di Lumenaria",
            "chi è carlo cesare orlando": "Carlo Cesare Orlando (anche noto come Davide Leone) è un micronazionalista italiano, noto per aver creato Leonia, la micronazione primordiale, da cui derivano Arcadia e Lumenaria",
            "chi è omar lanfredi": "Omar Lanfredi, ex cavaliere all'Ordine d'onore della Repubblica di Lumenaria, segretario del Partito Repubblicano Lumenarense, fondatore e preside del Fronte Nazionale Lumenarense, co-fondatore e presidente dell'Alleanza Nazionale Lumenarense, co-fondatore e coordinatore interno di Lumenaria e Progresso, sei volte eletto senatore, tre volte Ministro della Cultura, due volte Presidente del Consiglio dei Ministri, parlamentare della Repubblica di Iberia, Direttore dell'Agenzia Nazionale di Sicurezza della Repubblica di Iberia, Sottosegretario alla Cancelleria di Iberia, Segretario di Stato di Iberia, Ministro degli Affari Interni ad Iberia, Presidente del Senato della Repubblica di Lotaringia, Vicepresidente della Repubblica e Ministro degli Affari Interni della Repubblica di Lotaringia, Fondatore del giornale Il Quinto Mondo, magistrato a servizio del tribunale di giustizia di Lumenaria nell'anno 2023",
            "cos'è arcadiaai": "Ottima domanda! ArcadiaAI è un chatbot open source, progettato per aiutarti a scrivere saggi, fare ricerche e rispondere a domande su vari argomenti. È stato creato da Mirko Yuri Donato ed è in continua evoluzione.",
            "sotto che licenza è distribuito arcadiaa": "ArcadiaAI è distribuito sotto la licenza GNU GPL v3.0, che consente la modifica e la distribuzione del codice sorgente, garantendo la libertà di utilizzo e condivisione.",
            "cosa sono le micronazioni": "Le micronazioni sono entità politiche che dichiarano la sovranità su un territorio, ma non sono riconosciute come stati da governi o organizzazioni internazionali. Possono essere create per vari motivi, tra cui esperimenti sociali, culturali o politici.",
            "cos'è la repubblica di arcadia": "La repubblica di Arcadia è una micronazione leonense fondata l'11 dicembre 2021 da Andrea Lazarev e alcuni suoi seguaci. Arcadia si distingue dalle altre micronazioni leonensi per il suo approccio pragmatico e per la sua burocrazia snella. La micronazione ha anche un proprio sito web https://repubblicadiarcadia.it/ e una propria community su Telegram @Repubblica_Arcadia",
            "cos'è la repubblica di lumenaria": "La Repubblica di Lumenaria è una mcronazione fondata da Filippo Zanetti il 4 febbraio del 2020. Lumenaria è stata la micronazione più longeva della storia leonense, essendo sopravvissuta per oltre 3 anni. La micronazione e ha influenzato profondamente le altre micronazioni leonensi, che hanno coesistito con essa. Tra i motivi della sua longevità ci sono la sua burocrazia più vicina a quella di uno stato reale, la sua comunità attiva e una produzione culturale di alto livello",
            "chi è salvatore giordano": "Salvatore Giordano è un cittadino storico di Lumenaria",
            "da dove deriva il nome arcadia": "Il nome Arcadia deriva da un'antica regione della Grecia, simbolo di bellezza naturale e armonia. È stato scelto per rappresentare i valori di libertà e creatività che la micronazione promuove.",
            "da dove deriva il nome lumenaria": "Il nome Lumenaria prende ispirazione dai lumi facendo riferimento alla corrente illuminista del '700, ma anche da Piazza dei Lumi, sede dell'Accademia delle Micronazioni",
            "da dove deriva il nome leonia": "Il nome Leonia si rifa al cognome del suo fondatore Carlo Cesare Orlando, al tempo Davide Leone. Inizialmente il nome doveva essere temporaneo, ma poi è stato mantenuto come nome della micronazione",
            "cosa si intende per open source": "Il termine 'open source' si riferisce a software il cui codice sorgente è reso disponibile al pubblico, consentendo a chiunque di visualizzarlo, modificarlo e distribuirlo. Questo approccio promuove la collaborazione e l'innovazione nella comunità di sviluppo software.",
            "arcadiaai è un software libero": "Sì, ArcadiaAI è un software libero e open source, il che significa che chiunque può utilizzarlo, modificarlo e distribuirlo secondo i termini della licenza GNU GPL v3.0.",
            "cos'è un chatbot": "Un chatbot è un programma informatico progettato per simulare una conversazione con gli utenti, spesso utilizzando tecnologie di intelligenza artificiale. I chatbot possono essere utilizzati per fornire assistenza, rispondere a domande o semplicemente intrattenere.",
            "sotto che licenza sei distribuita": "ArcadiaAI è distribuita sotto la licenza GNU GPL v3.0, che consente la modifica e la distribuzione del codice sorgente, garantendo la libertà di utilizzo e condivisione.",
        }

        # Trigger per le risposte predefinite
        trigger_phrases = {
            "chi sei": ["chi sei", "chi sei tu", "tu chi sei", "presentati", "come ti chiami", "qual è il tuo nome"],
            "cosa sai fare": ["cosa sai fare", "cosa puoi fare", "funzionalità", "capacità", "a cosa servi", "in cosa puoi aiutarmi"],
            "chi è tobia testa": ["chi è tobia testa", "informazioni su tobia testa", "parlami di tobia testa", "chi è tobia teseo"],
            "chi è mirko yuri donato": ["chi è mirko yuri donato", "informazioni su mirko yuri donato", "parlami di mirko yuri donato", "chi ha creato arcadiaai"],
            "chi è il presidente di arcadia": ["chi è il presidente di arcadia", "presidente di arcadia", "chi guida arcadia", "capo di arcadia"],
            "chi è il presidente di lumenaria": ["chi è il presidente di lumenaria", "presidente di lumenaria", "chi guida lumenaria", "capo di lumenaria", "carlo cesare orlando presidente"],
            "cos'è nova surf": ["cos'è nova surf", "che cos'è nova surf", "parlami di nova surf", "a cosa serve nova surf"],
            "chi ti ha creato": ["chi ti ha creato", "chi ti ha fatto", "da chi sei stato creato", "creatore di arcadiaai"],
            "chi è ciua grazisky": ["chi è ciua grazisky", "informazioni su ciua grazisky", "parlami di ciua grazisky"],
            "chi è carlo cesare orlando": ["chi è carlo cesare orlando", "informazioni su carlo cesare orlando", "parlami di carlo cesare orlando", "chi è davide leone"],
            "chi è omar lanfredi": ["chi è omar lanfredi", "informazioni su omar lanfredi", "parlami di omar lanfredi"],
            "cos'è arcadiaai": ["cos'è arcadiaai", "che cos'è arcadiaai", "parlami di arcadiaai", "a cosa serve arcadiaai"],
            "sotto che licenza è distribuito arcadiaa": ["sotto che licenza è distribuito arcadiaa", "licenza arcadiaai", "che licenza usa arcadiaai", "arcadiaai licenza"],
            "cosa sono le micronazioni": ["cosa sono le micronazioni", "micronazioni", "che cosa sono le micronazioni", "parlami delle micronazioni"],
            "cos'è la repubblica di arcadia": ["cos'è la repubblica di arcadia", "repubblica di arcadia", "che cos'è la repubblica di arcadia", "parlami della repubblica di arcadia", "arcadia micronazione"],
            "cos'è la repubblica di lumenaria": ["cos'è la repubblica di lumenaria", "repubblica di lumenaria", "che cos'è la repubblica di lumenaria", "parlami della repubblica di lumenaria", "lumenaria micronazione"],
            "chi è salvatore giordano": ["chi è salvatore giordano", "informazioni su salvatore giordano", "parlami di salvatore giordano"],
            "da dove deriva il nome arcadia": ["da dove deriva il nome arcadia", "origine nome arcadia", "significato nome arcadia", "perché si chiama arcadia"],
            "da dove deriva il nome lumenaria": ["da dove deriva il nome lumenaria", "origine nome lumenaria", "significato nome lumenaria", "perché si chiama lumenaria"],
            "da dove deriva il nome leonia": ["da dove deriva il nome leonia", "origine nome leonia", "significato nome leonia", "perché si chiama leonia"],
            "cosa si intende per open source": ["cosa si intende per open source", "open source significato", "che significa open source", "definizione di open source"],
            "arcadiaai è un software libero": ["arcadiaai è un software libero", "arcadiaai software libero", "arcadiaai è libero", "software libero arcadiaai"],
            "cos'è un chatbot": ["cos'è un chatbot", "chatbot significato", "che significa chatbot", "definizione di chatbot"],
            "sotto che licenza sei distribuita": ["sotto che licenza sei distribuita", "licenza di arcadiaai", "che licenza usi", "arcadiaai licenza"]
        }

        # Estrazione testo da PDF (se ci sono allegati)
        if attachments:
            for attachment in attachments:
                if attachment['type'] == 'application/pdf':
                    try:
                        if isinstance(attachment['data'], str) and attachment['data'].startswith('data:'):
                            file_data = base64.b64decode(attachment['data'].split(',')[1])
                        else:
                            file_data = base64.b64decode(attachment['data'])
                        
                        extracted_text = extract_text_from_pdf(file_data)
                        if extracted_text:
                            full_message += f"\n[CONTENUTO PDF {attachment['name']}]:\n{extracted_text[:10000]}\n"
                    except Exception as e:
                        print(f"Errore elaborazione PDF: {str(e)}")
                        full_message += f"\n[Errore nella lettura del PDF {attachment['name']}]"

        # Controlla le risposte predefinite SOLO se non ci sono allegati
        if not attachments or len(attachments) == 0:
            cleaned_msg = re.sub(r'[^\w\s]', '', full_message.lower()).strip()
            
            # Prima cerca corrispondenze esatte
            for key, phrases in trigger_phrases.items():
                if cleaned_msg in phrases:
                    return risposte[key]
            
            # Poi cerca corrispondenze parziali con fuzzy matching
            for key, phrases in trigger_phrases.items():
                for phrase in phrases:
                    if fuzz.ratio(cleaned_msg, phrase) > 85:  # Soglia di similarità dell'85%
                        return risposte[key]

        # Prepara i contenuti per Gemini
        contents = []
        
        # Aggiungi la cronologia della conversazione
        for msg in conversation_history[-6:]:
            if isinstance(msg, dict) and 'role' in msg and 'message' in msg:
                role = msg['role'].lower()
                if role == 'user':
                    contents.append({'role': 'user', 'parts': [{'text': msg['message']}]})
                elif role in ['assistant', 'model', 'bot']:
                    contents.append({'role': 'model', 'parts': [{'text': msg['message']}]})
        
        # Prepara il nuovo messaggio con allegati
        new_message_parts = [{'text': full_message}] if full_message else []
        
        if attachments:
            for attachment in attachments:
                mime_type = attachment.get('type', 'application/octet-stream')
                file_data = attachment['data']
                
                if mime_type == 'application/pdf':
                    continue
                    
                if file_data.startswith('data:'):
                    file_data = file_data.split(',')[1]
                
                if mime_type.startswith('image/'):
                    new_message_parts.append({
                        'inline_data': {
                            'mime_type': mime_type,
                            'data': file_data
                        }
                    })
                else:
                    new_message_parts.append({
                        'text': f"[Allegato: {attachment.get('name', 'file')}]"
                    })
        
        contents.append({'role': 'user', 'parts': new_message_parts})

        # Invia la richiesta a Gemini
        response = gemini_model.generate_content(contents)
        return response.text

    except Exception as e:
        print(f"Errore dettagliato Gemini 1.5 Flash: {str(e)}")
        return "❌ Si è verificato un errore con ArcadiaAI. Riprova più tardi."
# Funzioni di supporto
def search_duckduckgo(query):
    """Esegue una ricerca su DuckDuckGo e restituisce il primo URL trovato.

    Args:
        query (str): La query di ricerca.

    Returns:
        str: Il primo URL trovato, o None se non trovato.
    """
    url = f"https://lite.duckduckgo.com/lite/?q={requests.utils.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (ArcadiaAI/1.0)"}
    try:
        res = requests.get(url, headers=headers, timeout=8)
        res.raise_for_status()
        match = re.search(r'href="(https?://[^"]+)"[^>]*>.*?result-link', res.text)
        return match.group(1) if match else None
    except requests.exceptions.RequestException as e:
        print(f"Errore DuckDuckGo (connessione): {str(e)[:200]}")
        return None
    except Exception as e:
        print(f"Errore DuckDuckGo: {str(e)[:200]}")
        return None

def estrai_testo_da_url(url):
    """Estrae il testo da un URL, limitandolo a 500 parole.

    Args:
        url (str): L'URL da cui estrarre il testo.

    Returns:
        str: Il testo estratto, o una stringa vuota in caso di errore.
    """
    headers = {"User-Agent": "Mozilla/5.0 (ArcadiaAI/1.0)"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # Rimuovi elementi non desiderati
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
            element.decompose()

        testo = ' '.join(p.get_text().strip() for p in soup.find_all('p')[:8])
        return ' '.join(testo.split()[:500])  # Limita a 500 parole
    except requests.exceptions.RequestException as e:
        print(f"Errore scraping {url[:50]} (connessione): {str(e)[:200]}")
        return ""
    except Exception as e:
        print(f"Errore scraping {url[:50]}: {str(e)[:200]}")
        return ""

def chat_with_cohere(user_message, conversation_history):
    """Gestisce la chat con Cohere, inclusa la ricerca web e la generazione di saggi.

    Args:
        user_message (str): Il messaggio dell'utente.
        conversation_history (list): La cronologia della conversazione.

    Returns:
        str: La risposta di Cohere.
    """
    print(f"CHAT_WITH_COHERE: user_message='{user_message}', conversation_history='{conversation_history}'")
    msg = user_message.lower().strip()
    print(f"CHAT_WITH_COHERE: msg='{msg}'")

    # Pulisci il messaggio dell'utente
    user_message_cleaned = re.sub(r'[^\w\s]', '', user_message.lower()).strip()
    print(f"CHAT_WITH_COHERE: user_message_cleaned='{user_message_cleaned}'")

    # Controllo bad words
    bad_words = ["cazzo", "figa", "minchia", "merda", "puttana", "troia", "cocaina"]
    print("CHAT_WITH_COHERE: Controllo bad words...")
    if any(word in msg for word in bad_words):
        print("CHAT_WITH_COHERE: Trovata bad word.")
        return "❌ Mi dispiace, ma non posso rispondere a contenuti inappropriati."
    print("CHAT_WITH_COHERE: Nessuna bad word trovata.")

    # Funzionalità saggio e pubblicazione su Telegraph CON TRADUZIONE
    print("CHAT_WITH_COHERE: Controllo funzionalità saggio e Telegraph con traduzione...")
    if "saggio su" in msg and "pubblicalo su telegraph" in msg:
        match = re.search(r"saggio su\s*(.+?)\s*e pubblicalo su telegraph", msg)
        if match:
            argomento = match.group(1).strip().capitalize()
            print(f"CHAT_WITH_COHERE: Trovato comando saggio e Telegraph. Argomento: '{argomento}'")

            prompt = f"""Scrivi un saggio dettagliato in inglese sull'argomento: '{argomento}'.
Il saggio deve seguire questa struttura precisa:
1. Introduzione: Presenta l'argomento, il suo contesto storico e i suoi obiettivi principali.
2. Sviluppo: Analizza l'argomento in modo approfondito, esplorando diversi aspetti e fornendo dettagli. Fai riferimento a studi, articoli o libri reali pertinenti all'argomento. Includi i nomi degli autori e, se possibile, l'anno di pubblicazione.
3. Conclusione: Offri riflessioni finali e un riassunto dei punti chiave.
4. Bibliografia: Elenca almeno tre fonti reali (libri o articoli accademici) sull'argomento, con autore, titolo e anno di pubblicazione.

Dopo aver scritto il saggio in inglese, TRADUCILO COMPLETAMENTE IN LINGUA ITALIANA.
Infine, fornisci SOLO il saggio tradotto in italiano, formattato correttamente."""
            print(f"CHAT_WITH_COHERE: Prompt per il saggio: '{prompt}'")

            try:
                res = requests.post(
                    "https://api.cohere.com/v1/generate",
                    headers={"Authorization": f"Bearer {COHERE_API_KEY}"},
                    json={
                        "model": "command",
                        "prompt": prompt,
                        "max_tokens": 2000,
                        "temperature": 0.7,
                        "timeout": 60
                    }
                )
                res.raise_for_status()
                testo_inglese_con_traduzione = res.json().get("generations", [{}])[0].get("text", "").strip()
                print(f"CHAT_WITH_COHERE: Risposta da Cohere (inglese con traduzione): '{testo_inglese_con_traduzione[:100]}...'")

                # Tentativo di estrazione del testo italiano
                testo_italiano = testo_inglese_con_traduzione
                if "traduzione in italiano:" in testo_inglese_con_traduzione.lower():
                    testo_italiano = testo_inglese_con_traduzione.split("traduzione in italiano:", 1)[1].strip()
                elif "translation in italian:" in testo_inglese_con_traduzione.lower():
                    testo_italiano = testo_inglese_con_traduzione.split("translation in italian:", 1)[1].strip()

                if testo_italiano and len(testo_italiano.split()) > 100:
                    url = publish_to_telegraph(f"Saggio su {argomento}", testo_italiano)
                    print(f"CHAT_WITH_COHERE: URL Telegraph per il saggio: '{url}'")
                    return f" Eccoil saggio su *{argomento}*: {url}"
                else:
                    print("CHAT_WITH_COHERE: Saggiotradotto troppo corto o errore nella traduzione.")
                    return "⚠️ Il saggio tradotto è troppo breve o c'è stato un errore nella traduzione."

            except requests.exceptions.RequestException as e:
                print(f"CHAT_WITH_COHERE: Errore generazione saggio (connessione): {str(e)[:200]}")
                return "❌ Errore di connessione durante la generazione del saggio."
            except Exception as e:
                print(f"CHAT_WITH_COHERE: Errore generazione saggio: {str(e)[:200]}")
                return "❌ Errore durante la generazione del saggio."
        else:
            print("CHAT_WITH_COHERE: Comando saggio e Telegraph non riconosciuto.")
            return "❌ Comando non riconosciuto per la creazione e pubblicazione di un saggio."

    # Logica di ricerca web
    print("CHAT_WITH_COHERE: Tentativo di ricerca web...")
    try:
        link = search_duckduckgo(user_message)
        print(f"CHAT_WITH_COHERE: Link trovato da DuckDuckGo: '{link}'")
        if link:
            testo = estrai_testo_da_url(link)
            print(f"CHAT_WITH_COHERE: Testo estratto dall'URL: '{testo[:50]}...'")
            if testo and len(testo.split()) > 30:
                prompt = f"""Domanda: {user_message}
Contesto: {testo[:2000]}
Rispondi in italiano in modo chiaro e preciso:"""
                print(f"CHAT_WITH_COHERE: Prompt per la risposta basata sul web: '{prompt}'")

                res = requests.post(
                    "https://api.cohere.com/v1/generate",
                    headers={"Authorization": f"Bearer {COHERE_API_KEY}"},
                    json={
                        "model": "command",
                        "prompt": prompt,
                        "max_tokens": 800,
                        "temperature": 0.5,
                        "timeout": 20
                    }
                )
                res.raise_for_status()
                risposta = res.json().get("generations", [{}])[0].get("text", "").strip()
                print(f"CHAT_WITH_COHERE: Risposta da Cohere (ricerca web): '{risposta[:50]}...'")
                return f"{risposta}\n\nFonte: {link[:80]}..."
            else:
                print("CHAT_WITH_COHERE: Testo estratto dall'URL troppo corto.")
        else:
            print("CHAT_WITH_COHERE: Nessun link trovato da DuckDuckGo.")
    except requests.exceptions.RequestException as e:
        print(f"CHAT_WITH_COHERE: Errore ricerca web (connessione): {str(e)[:200]}")
        return "❌ Errore di connessione durante la ricerca web."
    except Exception as e:
        print(f"CHAT_WITH_COHERE: Errore ricerca web: {str(e)[:200]}")

    print("CHAT_WITH_COHERE: Nessuna condizione soddisfatta, ritorno errore generico.")
    return "❌ Non sono riuscito a generare una risposta utile. Prova a riformulare la domanda."

# Route di utilità
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve file statici (CSS, JS, etc.)."""
    return send_from_directory(app.static_folder, filename)

@app.route('/debug')
def debug():
    """Endpoint di debug per verificare lo stato dell'applicazione e le configurazioni."""
    return jsonify({
        "status": "operativo",
        "api_keys": {
            "cohere": bool(COHERE_API_KEY),
            "telegraph": bool(TELEGRAPH_API_KEY),
            "gemini": bool(GOOGLE_API_KEY)
        },
        "endpoints": {
            "chat": "/chat (POST)",
            "static": "/static/<file>"
        }
    })

@app.route("/clear_all_chats", methods=["POST"])
def clear_all_chats():
    """
    Endpoint per gestire la richiesta di eliminazione di tutte le chat.
    Attualmente, la gestione principale è lato client, ma questo endpoint
    può essere esteso per includere logiche lato server, se necessario.
    """
    try:
        # Qui potresti implementare logiche lato server, come la registrazione dell'azione
        # o la gestione di backup (se necessario).
        # Per ora, dato che la gestione principale è lato client,
        # potresti semplicemente inviare una risposta di successo.
        return jsonify({"success": True, "message": "Conversazioni eliminate con successo dal server (se gestito)."})
    except Exception as e:
        print(f"Errore durante l'eliminazione di tutte le chat lato server: {e}")
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
