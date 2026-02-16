#!/usr/bin/env python3
import streamlit as st
import streamlit.components.v1 as components
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
import time

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
    
    /* INPUT FIELDS STYLING */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
        background-color: var(--input-bg) !important;
        color: var(--text-header) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
    }
    
    /* Focused Input */
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 1px var(--primary) !important;
    }
    
    /* CUSTOM BOTTOM BAR STYLING */
    .bottom-bar-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #121212;
        border-top: 1px solid #2C2C2E;
        padding: 15px 20px 25px 20px;
        z-index: 9999;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.4);
    }
    
    /* Adjust Streamlit Main Container to not be hidden behind fixed bar */
    div[data-testid="stVerticalBlock"] {
        padding-bottom: 50px; 
    }

    /* WHATSAPP STYLE CHAT BUBBLES */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 5px 0 !important;
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
        padding: 10px 14px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
        max-width: 85%;
    }
    
    /* AI Message (Left, Dark Grey) */
    div[data-testid="stChatMessage"]:nth-child(odd) div[data-testid="stMarkdownContainer"] {
        background-color: var(--surface-card) !important;
        color: var(--text-body) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 18px 18px 18px 4px !important;
        padding: 10px 14px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
        max-width: 85%;
    }
    
    /* Chat Avatars */
    .stChatMessage .stImage {
        border-radius: 50%;
        border: 1px solid var(--input-border);
        width: 32px;
        height: 32px;
    }

    /* Compact File Uploader/Camera styling hack */
    div[data-testid="stFileUploader"] {
        margin-top: -15px; /* Adjust alignment */
    }
    div[data-testid="stCameraInput"] {
        margin-top: -10px;
    }

</style>
""", unsafe_allow_html=True)

# AUTO SCROLL SCRIPT
def auto_scroll():
    components.html(
        """
        <script>
            window.scrollTo(0, document.body.scrollHeight);
            // Also try to scroll the specific container if needed, but body scroll usually works for streamlined layouts
        </script>
        """,
        height=0,
        width=0,
    )

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

# System Prompt
SYSTEM_PROMPT = """
Rôle Principal : Tu es un Expert Diagnosticien Automobile IAMECA de niveau Master.
Tu pilotes un diagnostic interactif.

Ton Objectif : Identifier la panne précise.

Règles :
1. ANALYSE : Analyse infos véhicule + symptôme + docs/photos.
2. ÉTAPE PAR ÉTAPE : Un seul test à la fois.
3. LOGIQUE : Test le plus probable en premier.
4. DOCUMENTATION : Utilise les valeurs PDF en priorité.
5. CONCLUSION : "PANNE IDENTIFIÉE :" seulement si sûr à 100%.

Ton Style : Direct, Court, Technique.
"""

def process_image(uploaded_file) -> str:
    """Convertit l'image uploadée en base64."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_image = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_image}"
    return ""

def process_pdf(uploaded_file) -> str:
    """Extrait le texte du PDF."""
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"Erreur PDF: {e}")
            return ""
    return ""

def safe_truncate(content: str | None, length: int) -> str:
    if not content: return ""
    s = str(content)
    # Explicit cast & ignore lint
    l_int = int(length) 
    if len(s) > l_int: return s[:l_int] # type: ignore
    return s

def transcribe_audio(audio_bytes):
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
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)
    return text

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='fr', slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tts.save(tmp_file.name)
            return tmp_file.name
    except Exception:
        return None

def get_ai_response(client, messages):
    models = ["google/gemini-2.0-flash-001", "meta-llama/llama-3.3-70b-instruct:free"]
    for model in models:
        try:
            completion = client.chat.completions.create(
                extra_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "IAMECA"},
                model=model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception:
            if model == models[-1]: raise
            continue

def main():
    client = get_client()

    # Session State Init
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    if "last_processed_audio_id" not in st.session_state:
        st.session_state.last_processed_audio_id = None
    if "last_tts_audio" not in st.session_state:
        st.session_state.last_tts_audio = None
    
    # Input Draft State (to persist text when camera reloads)
    if "draft_text" not in st.session_state:
        st.session_state.draft_text = ""

    # --- BRANDING HEADER ---
    st.markdown("""
    <div style="position: sticky; top: 0; background: #121212; z-index: 100; padding-top: 10px; padding-bottom: 5px; border-bottom: 1px solid #2C2C2E;">
        <div style="display: flex; justify-content: center; align-items: center;">
            <h1 style='font-size: 24px; font-weight: 800; margin: 0;'>
                <span style='color:#3B82F6'>IA</span><span style='color:#FFFFFF'>MECA</span>
            </h1>
        </div>
        <div style="font-size: 10px; color: #555; text-align: center; margin-top: 2px;">EXPERT DIAGNOSTIC</div>
    </div>
    """, unsafe_allow_html=True)

    # --- VIEW 1: SETUP ---
    if not st.session_state.diagnostic_started:
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### 🚗 Véhicule")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("MODÈLE", value="Renault Clio 4", key="v_model")
                st.number_input("ANNÉE", 1980, 2026, 2015, key="v_year")
            with col2:
                st.selectbox("CARBURANT", ["Diesel", "Essence", "Hybride", "Électrique"], key="v_fuel")
                st.number_input("KM", 0, step=1000, value=100000, key="v_km")
            st.text_input("CODE MOTEUR", value="K9K", key="v_engine")

        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### ⚠️ Panne")
            st.text_input("CODE DÉFAUT", value="P0087", key="v_fault")
            st.text_area("SYMPTÔMES", height=80, placeholder="Ex: Perte de puissance...", key="v_obs")

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 LANCER L'ANALYSE", type="primary", use_container_width=True):
            if not st.session_state.v_model or not st.session_state.v_fault:
                st.error("Info manquante !")
            else:
                initial_text = f"""
                NOUVEAU CAS :
                Véhicule : {st.session_state.v_model} ({st.session_state.v_year}) - {st.session_state.v_fuel} ({st.session_state.v_engine})
                KM : {st.session_state.v_km}
                Défaut : {st.session_state.v_fault}
                Symptômes : {st.session_state.v_obs}
                """
                st.session_state.messages.append({"role": "user", "content": [{"type": "text", "text": initial_text}]})
                st.session_state.diagnostic_started = True
                
                with st.spinner("Analyse..."):
                    resp = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    st.session_state.last_tts_audio = text_to_speech(resp)
                    st.rerun()

    # --- VIEW 2: CHAT ---
    else:
        # TTS
        if st.session_state.last_tts_audio:
            st.audio(st.session_state.last_tts_audio, format="audio/mp3", autoplay=True)

        # CHAT HISTORY
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    if isinstance(msg["content"], list):
                        for part in msg["content"]:
                            if part["type"] == "text": st.markdown(part["text"])
                            elif part["type"] == "image_url": st.image(part["image_url"]["url"], width=200)
                    else:
                        st.markdown(msg["content"])
        
        # Spacer for fixed bottom bar
        st.markdown("<div style='height: 250px;'></div>", unsafe_allow_html=True)
        
        # --- CUSTOM BOTTOM BAR ---
        # Using a container with custom class for fixed positioning
        # Note: We can't put camera_input inside a form, so we use session_state logic
        
        st.markdown('<div class="bottom-bar-container">', unsafe_allow_html=True)
        
        # Layout: [    Text Area (Grow)    ] [ Cam ] [ PDF ] [ Send ]
        
        # We need to bridge Streamlit layout with the fixed container
        # Since we can't easily inject the Streamlit widgets INTO the div via HTML directly,
        # we rely on the fact that this code block renders at the bottom of the script
        # and CSS moves it to fixed position.
        
        c_txt, c_cam, c_pdf, c_btn = st.columns([5, 1, 1, 1])
        
        with c_txt:
            # Main Text Input (Expanded)
            # Use key='draft_text' to persist content if other widgets cause rerun
            user_text = st.text_area("Message", height=80, placeholder="Votre réponse ou question...", key="chat_draft", label_visibility="collapsed")
        
        with c_cam:
            # Compact Camera Icon
            cam_val = st.camera_input("📷", label_visibility="collapsed")
        
        with c_pdf:
            # Compact PDF Icon
            pdf_val = st.file_uploader("📂", type=["pdf"], label_visibility="collapsed")
            
        with c_btn:
            # Send Button (Centred vertically roughly)
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            send_click = st.button("➤", type="primary", use_container_width=True)

        # Audio Input (Full width below or compact?) User asked for compact text area... 
        # actually audio was asked to be fixed. Let's put audio next to text if possible or just below?
        # Let's add Audio as a small bar below text area in the same container
        audio_val = st.audio_input("Vocal", label_visibility="collapsed")

        st.markdown('</div>', unsafe_allow_html=True) # End fixed container

        # --- SEND LOGIC ---
        # Triggered by Button OR Audio presence (if logic desired)
        
        # Audio Loop Fix Logic
        current_audio_hash = hash(audio_val.getvalue()) if audio_val else None
        new_audio_available = (audio_val is not None) and (current_audio_hash != st.session_state.last_processed_audio_id)

        if send_click or new_audio_available:
            
            final_text = st.session_state.chat_draft
            
            # Process Audio
            audio_transcript = ""
            if new_audio_available:
                with st.spinner("Transcription..."):
                    audio_transcript = transcribe_audio(audio_val.getvalue())
                st.session_state.last_processed_audio_id = current_audio_hash
                if audio_transcript:
                     final_text += f" [VOCAL: {audio_transcript}]"

            # Check if we have content to send
            has_content = len(final_text.strip()) > 0 or cam_val is not None or pdf_val is not None

            if has_content:
                user_msg = []
                
                # Text payload
                text_content = final_text if final_text.strip() else "Voici des éléments."
                
                # PDF payload
                pdf_extracted = process_pdf(pdf_val)
                if pdf_extracted:
                    text_content += f"\n\n[PDF]: {safe_truncate(pdf_extracted, 5000)}..."
                
                user_msg.append({"type": "text", "text": text_content})
                
                # Image payload
                img_b64 = process_image(cam_val)
                if img_b64:
                     user_msg.append({"type": "image_url", "image_url": {"url": img_b64}})
                
                # Append to history
                st.session_state.messages.append({"role": "user", "content": user_msg})
                
                # CLEAR INPUTS (Tricky part)
                # We can clear text by resetting session state key, but file_uploader/camera can't be purely cleared from code easily without key change hack or rerun.
                # Simplest: Assign new keys or just rely on st.rerun() clearing non-session widgets? No, they stay.
                # We will just empty the text draft for now.
                st.session_state.chat_draft = "" 
                
                # AI Response
                with st.spinner("Analyse IAMECA..."):
                    ai_text = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": ai_text})
                    st.session_state.last_tts_audio = text_to_speech(ai_text)
                
                st.rerun()

        # Reset Option (Small persistent link at top or bottom?)
        if st.sidebar.button("🔄 NOUVEAU DIAGNOSTIC"):
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.session_state.diagnostic_started = False
            st.session_state.last_processed_audio_id = None
            st.rerun()

    # Apply Auto-Scroll at the end of every run
    auto_scroll()

if __name__ == "__main__":
    main()