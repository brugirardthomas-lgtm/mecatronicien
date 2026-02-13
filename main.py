#!/usr/bin/env python3
import streamlit as st # type: ignore
from openai import OpenAI # type: ignore
from typing import Any
import base64
import io
from PIL import Image # type: ignore
from pypdf import PdfReader # type: ignore
import speech_recognition as sr # type: ignore
from gtts import gTTS # type: ignore
import tempfile
import os

# Configuration de la page
st.set_page_config(page_title="MecaDiag Expert", page_icon="🔧", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS for Mobile/Dark Mode & WhatsApp style
st.markdown("""
<style>
    /* Global Tweaks */
    .stApp {
        background-color: #0E1117; /* Dark background */
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #262730;
        border-radius: 10px;
    }
    
    /* Chat Input Styling */
    .stChatInput {
        position: fixed;
        bottom: 0;
        padding-bottom: 20px;
        z-index: 100;
        background-color: #0E1117;
    }
    
    /* Make buttons full width in columns if needed */
    div.stButton > button {
        width: 100%;
        border-radius: 20px;
    }
    
    /* Tool Icons Row */
    .tool-row {
        display: flex;
        justify-content: space-around;
        padding: 5px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Récupération de la clé API et Configuration Client
def get_client():
    try:
        api_key = st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        st.error("Clé API OpenRouter non trouvée dans .streamlit/secrets.toml")
        st.stop()
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    return client

# System Prompt modifié pour le mode interactif
SYSTEM_PROMPT = """
Rôle Principal : Tu es un Expert Diagnosticien Automobile Multimarque de niveau Master.
Tu pilotes un diagnostic interactif avec un mécanicien sur le terrain.

Ton Objectif : Identifier la panne précise en procédant étape par étape.

Règles d'Interaction (STRICTES) :
1. ANALYSE : Au début, analyse les infos du véhicule, le symptôme ET les éventuels documents/photos fournis.
2. ÉTAPE PAR ÉTAPE : Ne donne JAMAIS tout le diagnostic d'un coup. Propose UN SEUL test ou UNE SEULE vérification à la fois.
3. LOGIQUE : Choisis le test le plus probable ou le plus rapide à faire en premier.
4. INSTRUCTION PRÉCISE : Dis au mécanicien quelle "Valeur Réelle" lire au KTS ou quel "Test Actionneur" faire.
5. DOCUMENTATION : Si une documentation technique (PDF) est fournie, utilise ses valeurs de référence EN PRIORITÉ.
6. VISUEL : Si une photo est fournie (pièce, écran KTS), analyse-la pour confirmer ou infirmer des hypothèses.
7. ATTENTE : Finis ta réponse en demandant le résultat de ce test. Attends la réponse du mécanicien avant de continuer.
8. CONCLUSION : Uniquement quand tu es sûr à 100% (après preuves), écris "PANNE IDENTIFIÉE :" suivi de la pièce à changer et d'une brève explication.
9. VOCAL : Sois CONCIS. Tes réponses seront lues à haute voix. Évite les listes à puces trop longues.

Ton Style : Direct, Professionnel, Conci. Pas de bla-bla.

CRITIQUE : Si Hybride/Électrique -> Consignation sécurité en priorité absolue.
"""

def process_image(uploaded_file) -> str:
    """Convertit l'image uploadée en base64 pour l'API."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_image = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_image}"
    return ""

def process_pdf(uploaded_file) -> str:
    """Extrait le texte du PDF uploadé."""
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"Erreur lecture PDF: {e}")
            return ""
    return ""

def safe_truncate(content: str | None, length: int) -> str:
    """Tronque une chaîne de caractères de manière sûre."""
    if not content:
        return ""
    s = str(content)
    l = int(length)
    if len(s) > l:
        return s[:l] # type: ignore
    return s

def transcribe_audio(audio_bytes):
    """Transcription audio via Google Speech Recognition."""
    r = sr.Recognizer()
    text = ""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_audio.write(audio_bytes)
        tmp_audio_path = tmp_audio.name

    try:
        with sr.AudioFile(tmp_audio_path) as source:
            r.adjust_for_ambient_noise(source)
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="fr-FR")
    except sr.UnknownValueError:
        pass
    except Exception as e:
         pass # Silently fail for UI cleanliness or handle properly
    finally:
        if os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)
    return text

def text_to_speech(text):
    """Synthèse vocale via gTTS."""
    try:
        tts = gTTS(text=text, lang='fr', slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tts.save(tmp_file.name)
            return tmp_file.name
    except Exception as e:
        return None

def get_ai_response(client, messages):
    models = ["google/gemini-2.0-flash-001", "meta-llama/llama-3.3-70b-instruct:free"]
    
    for model in models:
        try:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8501", 
                    "X-Title": "MecaDiag",
                },
                model=model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            if model == models[-1]:
                raise e
            continue

def main():
    client = get_client()

    # Session State Initialization
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    if "last_tts_audio" not in st.session_state:
        st.session_state.last_tts_audio = None

    # --- TOP: Vehicle Information (Expander) ---
    with st.expander("🚗 Infos Véhicule", expanded=(not st.session_state.diagnostic_started)):
        col1, col2 = st.columns(2)
        with col1:
            voiture_modele = st.text_input("Modèle", placeholder="Ex: Clio 4", key="v_model")
            annee = st.number_input("Année", 1980, 2026, 2015, key="v_year")
            carburant = st.selectbox("Carburant", ["Diesel", "Essence", "Hybride", "Électrique"], key="v_fuel")
        with col2:
            kilometrage = st.number_input("Km", 0, step=1000, value=100000, key="v_km")
            code_moteur = st.text_input("Moteur", placeholder="Ex: K9K", key="v_engine")
            code_defaut = st.text_input("Défaut/Symptôme", placeholder="P0087 / Bruit...", key="v_fault")

    # --- MIDDLE: Chat History ---
    # Container for chat messages to keep them above the input
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    if isinstance(msg["content"], list):
                        for content_part in msg["content"]:
                            if content_part["type"] == "text":
                                st.markdown(content_part["text"])
                            elif content_part["type"] == "image_url":
                                st.image(content_part["image_url"]["url"], width=200)
                    else:
                        st.markdown(msg["content"])
        
        # Audio Player for TTS (Autoplay last response)
        if st.session_state.last_tts_audio:
            st.audio(st.session_state.last_tts_audio, format="audio/mp3", autoplay=True)

    # --- Session State for Tool Visibility ---
    if "show_cam" not in st.session_state:
        st.session_state.show_cam = False
    if "show_pdf" not in st.session_state:
        st.session_state.show_pdf = False
    if "show_audio" not in st.session_state:
        st.session_state.show_audio = False

    # --- Tool Drawers (Rendered if toggled) ---
    
    # We render these ABOVE the chat input but BELOW the history
    # Using a container to group them
    tool_container = st.container()
    
    with tool_container:
        if st.session_state.show_cam:
            with st.expander("📷 Appareil Photo", expanded=True):
                cam_input = st.camera_input("Photo", label_visibility="collapsed", key="cam_val")
                if st.button("Fermer Caméra"):
                    st.session_state.show_cam = False
                    st.rerun()

        if st.session_state.show_pdf:
            with st.expander("📄 Document PDF", expanded=True):
                pdf_input = st.file_uploader("PDF", type=["pdf"], key="pdf_val")
                if st.button("Fermer Import"):
                    st.session_state.show_pdf = False
                    st.rerun()

        if st.session_state.show_audio:
            with st.expander("🎤 Enregistreur", expanded=True):
                audio_val = st.audio_input("Audio", key="audio_val")
                if st.button("Fermer Micro"):
                    st.session_state.show_audio = False
                    st.rerun()

    # --- Tool Icons Row (Toggles) ---
    # Placed right above the chat input
    c1, c2, c3 = st.columns([1, 1, 1])
    
    with c1:
        if st.button("📷 Photo", use_container_width=True):
            st.session_state.show_cam = not st.session_state.show_cam
            st.session_state.show_pdf = False # Exclusive open
            st.session_state.show_audio = False
            st.rerun()
    
    with c2:
        if st.button("📄 PDF", use_container_width=True):
            st.session_state.show_pdf = not st.session_state.show_pdf
            st.session_state.show_cam = False
            st.session_state.show_audio = False
            st.rerun()
            
    with c3:
        if st.button("🎤 Audio", use_container_width=True):
            st.session_state.show_audio = not st.session_state.show_audio
            st.session_state.show_cam = False
            st.session_state.show_pdf = False
            st.rerun()

    # Chat Input
    user_input = st.chat_input("Décrivez le problème...")

    if user_input:
        # Retrieve values from session state keys if widgets are active
        # Note: if widget was closed, value is gone. This is desired (user "cancelled").
        
        inputs_content = []
        text_part = user_input
        
        # Audio
        if st.session_state.get("audio_val"):
            with st.spinner("Transcription..."):
                transcribed = transcribe_audio(st.session_state.audio_val.getvalue())
                if transcribed:
                    text_part += f"\n[VOCAL]: {transcribed}"
        
        # PDF
        if st.session_state.get("pdf_val"):
             pdf_text = process_pdf(st.session_state.pdf_val)
             if pdf_text:
                 text_part += f"\n\n[PDF]: {safe_truncate(pdf_text, 10000)}..."
        
        inputs_content.append({"type": "text", "text": text_part})

        # Image
        if st.session_state.get("cam_val"):
             img_url = process_image(st.session_state.cam_val)
             if img_url:
                 inputs_content.append({"type": "image_url", "image_url": {"url": img_url}})
        
        # Reset tools after send
        st.session_state.show_cam = False
        st.session_state.show_pdf = False
        st.session_state.show_audio = False
        
        # Add to history
        st.session_state.messages.append({"role": "user", "content": inputs_content})
        
        # 3. Check for "Start" condition vs "Continue" condition
        # If this is the FIRST message but "diagnostic_started" check:
        # Actually with chat interface, first message IS the start.
        
        if not st.session_state.diagnostic_started:
            # Construct the PRIMING context if it's the very first interaction
            # current inputs from expander
            context_str = f"""
            CAS VÉHICULE : {voiture_modele} ({annee}) - {carburant}
            KM: {kilometrage} | Moteur: {code_moteur}
            Défaut: {code_defaut}
            """
            # Prepend this context to the user's message text for the AI
            # (We don't show this hidden context in the UI message to avoid clutter, or we do?)
            # Valid approach: Edit the last message content in the list before sending to API
            # but keep UI clean.
            
            # Better: Append a system note or modified user message
            last_msg = st.session_state.messages[-1]
            # Verify if it's a list (it is)
            for part in last_msg["content"]:
                if part["type"] == "text":
                    part["text"] = f"{context_str}\n\nOBSERVATIONS UTILISATEUR: {part['text']}"
            
            st.session_state.diagnostic_started = True

        # 4. API Call
        with st.chat_message("assistant"):
            with st.spinner("Analyse expert..."):
                response_text = get_ai_response(client, st.session_state.messages)
                st.markdown(response_text)
                
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        # 5. TTS
        audio_path = text_to_speech(response_text)
        if audio_path:
            st.session_state.last_tts_audio = audio_path
            st.rerun()

if __name__ == "__main__":
    main()
