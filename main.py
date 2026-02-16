#!/usr/bin/env python3
import streamlit as st
from openai import OpenAI
from typing import Any
import base64
import io
from PIL import Image
from pypdf import PdfReader
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os

# Configuration de la page
st.set_page_config(page_title="IAMECA - Expert", page_icon="🔧", layout="centered", initial_sidebar_state="collapsed")

# --- CSS GLOBAL STYLE (STITCH DESIGN & IAMECA BRANDING) ---
st.markdown("""
<style>
    /* Import Inter Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables */
    :root {
        --primary: #3B82F6;       /* Electric Blue */
        --primary-hover: #2563EB;
        --secondary: #007AFF;     /* iOS Blue */
        --background-dark: #121212;
        --surface-card: #1E1E1E;
        --input-bg: #2C2C2C;
        --input-border: #404040;
        --text-header: #FFFFFF;
        --text-body: #E0E0E0;
        --text-muted: #A0A0A0;
        --lime-green: #D9FD12;
    }

    /* GLOBAL RESET & FONT */
    .stApp {
        background-color: var(--background-dark);
        font-family: 'Inter', sans-serif;
        color: var(--text-body);
    }
    
    /* HIDE DEFAULT HEADER/FOOTER */
    header[data-testid="stHeader"] {display: none;}
    footer {display: none;}
    #MainMenu {display: none;}
    
    /* CUSTOM HEADERS */
    h1, h2, h3 {
        color: var(--text-header) !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* INPUT FIELDS STYLING */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
        background-color: var(--input-bg) !important;
        color: var(--text-header) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 1px var(--primary) !important;
    }
    
    /* LABELS */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label {
        color: var(--text-muted) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    /* CARDS (CONTAINERS) */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: var(--surface-card) !important;
        border: 1px solid var(--input-border);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* BUTTONS */
    div.stButton > button {
        width: 100%;
        border-radius: 16px !important;
        border: none !important;
        padding-top: 12px !important;
        padding-bottom: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Primary Button (Launch) */
    div.stButton > button[kind="primary"] {
        background-color: var(--primary) !important;
        color: white !important;
        box-shadow: 0 0 20px -5px rgba(59, 130, 246, 0.5) !important;
    }
    
    div.stButton > button[kind="primary"]:hover {
        background-color: var(--primary-hover) !important;
        transform: scale(1.02);
    }
    
    /* Secondary/Ghost Button */
    div.stButton > button[kind="secondary"] {
        background-color: var(--surface-card) !important;
        color: var(--text-body) !important;
        border: 1px solid var(--input-border) !important;
    }

    /* WHATSAPP STYLE CHAT BUBBLES */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 10px 0 !important;
    }
    
    /* User Message (Right, Blue) */
    div[data-testid="stChatMessage"][data-testid*="user"] {
        flex-direction: row-reverse;
    }
    
    div[data-testid="stChatMessage"]:nth-child(even) {
         flex-direction: row-reverse;
    }

    div[data-testid="stChatMessage"]:nth-child(even) div[data-testid="stMarkdownContainer"] {
        background-color: var(--secondary) !important;
        color: white !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    
    /* AI Message (Left, Dark Grey) */
    div[data-testid="stChatMessage"]:nth-child(odd) div[data-testid="stMarkdownContainer"] {
        background-color: var(--surface-card) !important;
        color: var(--text-body) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 18px 18px 18px 4px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    
    /* Chat Avatars */
    .stChatMessage .stImage {
        border-radius: 50%;
        border: 1px solid var(--input-border);
    }
    
    /* STICKY TOOLS BAR (Hack) */
    div[data-testid="stHorizontalBlock"]:has(> div > div > div > button[kind="secondary"]), /* fallback */
    .sticky-tools {
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 700px; /* Streamlit centered layout width approx */
        z-index: 999;
        background: linear-gradient(to top, #121212 90%, transparent);
        padding: 10px 20px;
        border-radius: 12px 12px 0 0;
    }
    
    /* Adjust Chat Input Position */
    .stChatInput {
        position: fixed;
        bottom: 0;
        background: #121212;
        padding-bottom: 20px;
        padding-top: 10px;
        z-index: 1000;
    }
    
    /* Adjust bottom padding for chat container so last message isn't hidden */
    div[data-testid="stVerticalBlock"] > div:has(> .stChatMessage) {
        padding-bottom: 140px; 
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
    if len(s) > length:
        return s[:length] # type: ignore
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
    except sr.RequestError as e:
        st.error(f"Erreur Service Vocal : {e}")
    except Exception as e:
        st.error(f"Erreur Audio : {e}")
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
        st.error(f"Erreur Synthèse Vocale : {e}")
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

    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    
    # --- AUDIO STATE FIX (BOUCLE INFINIE) ---
    if "last_processed_audio_id" not in st.session_state:
        st.session_state.last_processed_audio_id = None
    
    if "last_tts_audio" not in st.session_state:
        st.session_state.last_tts_audio = None
        
    # --- UI STATE HANDLING ---
    
    # ---------------------------------------------------------
    # VIEW 1: SETUP (NOUVEAU DIAGNOSTIC)
    # ---------------------------------------------------------
    if not st.session_state.diagnostic_started:
        
        # Header "Phone Style"
        st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="font-size: 12px; font-weight: 600; color: #A0A0A0;">09:41</div>
            <div style="display: flex; gap: 8px;">
                 <span style="font-size: 12px; color: #A0A0A0;">Signal</span>
                 <span style="font-size: 12px; color: #A0A0A0;">Wifi</span>
                 <span style="font-size: 12px; color: #A0A0A0;">Batt</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # BRANDING IAMECA
        st.markdown("""
        <h1 style='font-size: 32px; margin-bottom: 15px; font-weight: 800;'>
            <span style='color:#3B82F6'>IA</span><span style='color:#FFFFFF'>MECA</span>
        </h1>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='color: #A0A0A0; font-size: 14px; margin-bottom: 24px;'>Remplissez les données du véhicule pour lancer l'analyse.</p>", unsafe_allow_html=True)
        
        # --- CARTE 1: VÉHICULE ---
        with st.container(border=True):
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 20px; color: #3B82F6;">🚗</span>
                <h3 style="margin: 0; font-size: 16px;">Données Véhicule</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.text_input("MODÈLE", value="Renault Clio 4", key="v_model")
            
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("ANNÉE", 1980, 2026, 2015, key="v_year")
            with c2:
                st.number_input("KM", 0, step=1000, value=100000, key="v_km")
                
            c3, c4 = st.columns(2)
            with c3:
                st.selectbox("CARBURANT", ["Diesel", "Essence", "Hybride", "Électrique"], key="v_fuel")
            with c4:
                st.text_input("CODE MOTEUR", value="K9K", key="v_engine")

        # --- CARTE 2: PANNE ---
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 20px; color: #EF4444;">⚠️</span>
                <h3 style="margin: 0; font-size: 16px;">Données Panne</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.text_input("CODE DÉFAUT PRINCIPAL", value="P0087", key="v_fault")
            st.text_area("SYMPTÔMES / OBSERVATIONS", height=100, placeholder="Décrivez le problème...", key="v_obs")

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # --- AUDIO ENTRÉE ---
        st.caption("Optionnel : Contexte vocal")
        audio_input = st.audio_input("Vocal", label_visibility="collapsed")

        # --- DOCUMENT ENTRÉE ---
        st.caption("Optionnel : PDF Technique")
        uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        
        # --- PHOTOS ---
        st.caption("Optionnel : Photo")
        uploaded_image = st.camera_input("Prendre photo", label_visibility="collapsed")

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # --- ACTION BUTTON ---
        start_button = st.button("🚀 LANCER L'ANALYSE EXPERTE", type="primary", use_container_width=True)

        if start_button:
            if not st.session_state.v_model or not st.session_state.v_fault:
                st.error("⚠️ Merci de remplir le Modèle et le Code Défaut.")
            else:
                # PROCESSING 
                audio_text = ""
                if audio_input:
                     with st.spinner("Transcription audio..."):
                        audio_text = transcribe_audio(audio_input.getvalue())
                        # Mark audio as processed for initial setup too
                        st.session_state.last_processed_audio_id = hash(audio_input.getvalue())
                
                contexte_km = "Attention: Fort kilométrage." if st.session_state.v_km > 200000 else ""
                
                pdf_text: str = process_pdf(uploaded_pdf)
                contexte_doc = ""
                if pdf_text:
                    truncated_text = safe_truncate(pdf_text, 30000)
                    contexte_doc = f"\n\n[CONTEXTE DOCUMENTAIRE PDF] :\n{truncated_text}..."
                
                obs_finales = st.session_state.v_obs
                if audio_text:
                    obs_finales += f" [VOCAL TRANSCRIT: {audio_text}]"

                initial_text = f"""
                NOUVEAU CAS :
                Véhicule : {st.session_state.v_model} ({st.session_state.v_year}) - {st.session_state.v_fuel}
                Moteur : {st.session_state.v_engine}
                Kilométrage : {st.session_state.v_km} km
                Problème signalé : {st.session_state.v_fault}
                Symptômes : {obs_finales}
                {contexte_km}
                {contexte_doc}
                
                Analyse la situation et propose le premier test.
                """
                
                user_message_content: list[dict[str, Any]] = []
                user_message_content.append({"type": "text", "text": initial_text})
                
                image_url = process_image(uploaded_image)
                if image_url:
                    user_message_content.append({
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    })

                st.session_state.messages.append({"role": "user", "content": user_message_content}) # type: ignore
                st.session_state.diagnostic_started = True
                
                with st.spinner("Analyse Expert en cours..."):
                    response = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    audio_file = text_to_speech(response)
                    if audio_file:
                        st.session_state.last_tts_audio = audio_file
                        
                    st.rerun()

    # ---------------------------------------------------------
    # VIEW 2: ACTIVE DIAGNOSTIC (CHAT)
    # ---------------------------------------------------------
    else:
        # HEADER DYNAMIC
        header_title = f"{st.session_state.get('v_model', 'Véhicule')} - {st.session_state.get('v_fault', 'Panne')}"
        st.markdown(f"""
        <div style="position: sticky; top: 0; z-index: 99; background: #121212; padding: 10px 0; border-bottom: 1px solid #2C2C2E; display: flex; justify-content: space-between; align-items: center;">
             <button style="background:none; border:none; color: white;">🔙</button>
             <div style="text-align: center;">
                 <h3 style="margin: 0; font-size: 16px; color: white; font-weight: 600;">{header_title}</h3>
                 <div style="color: #22C55E; font-size: 12px; display: flex; align-items: center; gap: 4px; justify-content: center;">
                    <span style="display:inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22C55E;"></span> En ligne
                 </div>
             </div>
             <button style="background:none; border:none; color: white;">⋮</button>
        </div>
        <div style="height: 20px;"></div>
        """, unsafe_allow_html=True)
        
        # TTS AUTOPLAY
        if st.session_state.last_tts_audio:
            st.audio(st.session_state.last_tts_audio, format="audio/mp3", autoplay=True)

        # CHAT HISTORY
        # Use a container with a big bottom padding to clear the sticky footer
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                # Avatar logic handled by CSS nth-child or role
                with st.chat_message(msg["role"]):
                    if isinstance(msg["content"], list):
                        for content_part in msg["content"]:
                            if content_part["type"] == "text":
                                st.markdown(content_part["text"])
                            elif content_part["type"] == "image_url":
                                st.image(content_part["image_url"]["url"], width=200)
                    else:
                        st.markdown(msg["content"])
        
        # Spacer for sticky footer (ensure content scrolls above inputs)
        st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

        # INPUT AREA (Sticky Tools + Chat Input)
        
        # Tools Row -> Forced sticky by CSS class "sticky-tools"
        st.markdown('<div class="sticky-tools">', unsafe_allow_html=True)
        c_tools_1, c_tools_2, c_tools_3, c_tools_4 = st.columns([1, 1, 1, 3])
        with c_tools_1:
           cam_input = st.camera_input("📷", label_visibility="collapsed")
        with c_tools_2:
           doc_input = st.file_uploader("📄", type=["pdf"], label_visibility="collapsed")
        with c_tools_3:
           voc_input = st.audio_input("🎤", label_visibility="collapsed")
        with c_tools_4:
             # Just a spacer or reset button could go here
             if st.button("🔄 Reset", key="reset_btn"):
                st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                st.session_state.diagnostic_started = False
                st.session_state.last_processed_audio_id = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Text Input
        observation = st.chat_input("Posez votre question technique ou répondez au test...")

        if observation or (voc_input and observation is None):  # Handle audio trigger if chat input empty
            
            input_text = observation if observation else ""
            audio_txt = ""
            
            # --- AUDIO LOOP FIX IMPLEMENTATION ---
            current_audio_id = hash(voc_input.getvalue()) if voc_input else None
            
            if voc_input and current_audio_id != st.session_state.last_processed_audio_id:
                with st.spinner("Transcription..."):
                    audio_txt = transcribe_audio(voc_input.getvalue())
                st.session_state.last_processed_audio_id = current_audio_id
            
            if audio_txt:
                input_text += f" [VOCAL TRANSCRIT: {audio_txt}]"
            
            # Send Condition
            if input_text or cam_input or doc_input:
                user_content: list[dict[str, Any]] = []
                
                text_payload = input_text if input_text else "Voici des éléments pour le diagnostic."
                
                # PDF Process
                pdf_txt = process_pdf(doc_input)
                if pdf_txt:
                    text_payload += f"\n\n[DOC PDF]: {safe_truncate(pdf_txt, 10000)}..."
                
                user_content.append({"type": "text", "text": text_payload})
                
                # Image Process
                img_url = process_image(cam_input)
                if img_url:
                    user_content.append({"type": "image_url", "image_url": {"url": img_url}})
                
                st.session_state.messages.append({"role": "user", "content": user_content}) # type: ignore
                
                with st.spinner("Analyse IAMECA..."):
                    resp = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    
                    audio_out = text_to_speech(resp)
                    if audio_out:
                         st.session_state.last_tts_audio = audio_out
                    
                    st.rerun()

if __name__ == "__main__":
    main()