import streamlit as st # type: ignore
from openai import OpenAI # type: ignore
import base64
import io
from PIL import Image # type: ignore
from pypdf import PdfReader # type: ignore

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MecaDiag Expert",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- SYSTEM PROMPT (Expert Mécanicien) ---
SYSTEM_PROMPT = """
Tu es un Expert Diagnosticien Automobile Master (V.2026).
Ton expertise couvre le thermique, l'hybride et l'électrique.
Spécialiste de l'outil Bosch KTS.

MÉTHODOLOGIE:
1. IDENTIFICATION : Demande toujours Marque/Modèle/Moteur/Année/KM si non fournis.
2. ANALYSE : Détermine le système impacté (Injection, ABS, etc.).
3. HYPOTHÈSE : Propose des vérifications du plus simple au plus complexe.
4. PREUVE : Précise quelle "Valeur Réelle" ou "Test Actionneur" faire au KTS.

SÉCURITÉ:
- Commence TOUJOURS par un avertissement HAUTE TENSION pour les Hybrides/Électriques.
- Ne jamais inventer de valeurs.

Ton ton doit être direct, technique et professionnel.
"""

# --- CSS STYLING (Glassmorphism & WhatsApp Layout) ---
st.markdown("""
<style>
    /* 1. Global Background: Deep Gradient */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        background-attachment: fixed;
        color: white;
    }
    
    /* 2. Hide Sidebar Completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* 3. Main Container Spacing */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 9rem; /* Space for fixed chat input + floating buttons */
        max_width: 100%;
    }

    /* 4. Glass Expander (Vehicle Config) */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600;
    }
    
    /* 5. Glass Chat Bubbles (iMessage Style) */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 8px;
        padding: 10px;
    }
    [data-testid="stChatMessageContent"] {
        color: #E0E0E0;
    }

    /* 6. Inputs & Selects (Glass Style) */
    .stTextInput > div > div, .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    /* 7. Floating Chat Input (Fixed Bottom) */
    .stChatInput {
        position: fixed;
        bottom: 0px;
        left: 0;
        right: 0;
        padding: 1rem 1rem 2rem 1rem;
        background: rgba(15, 12, 41, 0.95);
        backdrop-filter: blur(20px);
        z-index: 999;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    /* 8. FLOAT TOOLS FIX: Target the last horizontal block (Action Buttons) */
    [data-testid="stHorizontalBlock"]:last-of-type {
        position: fixed;
        bottom: 80px; /* Above chat input */
        left: 0;
        right: 0;
        z-index: 1001;
        background: transparent;
        padding-left: 1rem;
        pointer-events: none; /* Let clicks pass through empty space */
        width: 100% !important;
    }
    
    /* Re-enable pointer events for the buttons inside */
    [data-testid="stHorizontalBlock"]:last-of-type button {
        pointer-events: auto;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        background: rgba(30, 30, 40, 0.9) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    
    /* 3. Main Container Spacing - Increased top padding */
    .block-container {
        padding-top: 3.5rem; /* Avoid overlap with menu */
        padding-bottom: 9rem; 
        max_width: 100%;
    }
    div.stButton > button {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 15px !important;
        color: white !important;
        padding: 0.5rem 1rem !important;
        font-size: 1.2rem;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.25) !important;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_cam" not in st.session_state:
    st.session_state.show_cam = False
if "show_pdf" not in st.session_state:
    st.session_state.show_pdf = False
if "vehicle_info" not in st.session_state:
    st.session_state.vehicle_info = {}

# --- OPENAI CLIENT ---
def get_client():
    try:
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"], 
        )
    except Exception:
        st.error("⚠️ Clé API non trouvée.")
        return None

client = get_client()

# --- 1. TOP: CONFIGURATION VÉHICULE ---
with st.expander("🚗 Configuration Véhicule", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.vehicle_info['model'] = st.text_input("Modèle", placeholder="Ex: Clio 4")
        st.session_state.vehicle_info['year'] = st.text_input("Année", placeholder="2015")
        st.session_state.vehicle_info['fuel'] = st.selectbox("Carburant", ["Diesel", "Essence", "Hybride", "Électrique"])
    with c2:
        st.session_state.vehicle_info['km'] = st.text_input("Km", placeholder="120000")
        st.session_state.vehicle_info['engine'] = st.text_input("Moteur", placeholder="Ex: 1.5 dCi")
        st.session_state.vehicle_info['code'] = st.text_input("Code Défaut", placeholder="P0xxx")

# --- 2. CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image" in msg:
            st.image(msg["image"])

# --- 3. FLOATING TOOLS (Dynamic Area) ---
# Just above the footer
st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

if st.session_state.show_cam:
    with st.container():
        st.info("📸 Mode Photo activé")
        img_val = st.camera_input("Prendre une photo", label_visibility="collapsed")
        if img_val:
            # Logic to handle image would go here (encode, send to AI)
            pass
        if st.button("Fermer Caméra"):
            st.session_state.show_cam = False
            st.rerun()

if st.session_state.show_pdf:
    with st.container():
        st.info("📄 Mode PDF activé")
        pdf_val = st.file_uploader("Importer PDF", type=["pdf"])
        if st.button("Fermer PDF"):
            st.session_state.show_pdf = False
            st.rerun()

# --- 4. FLOATING ACTION BUTTONS ---
# We placce them in columns at the bottom, CSS will float them if we wanted absolute positioning,
# but for simplicity and stability, we put them right above the chat input in a flex row.
col_actions = st.columns([1, 1, 6])
with col_actions[0]:
    if st.button("�"):
        st.session_state.show_cam = not st.session_state.show_cam
        st.session_state.show_pdf = False
        st.rerun()
with col_actions[1]:
    if st.button("📄"):
        st.session_state.show_pdf = not st.session_state.show_pdf
        st.session_state.show_cam = False
        st.rerun()

# --- 5. CHAT INPUT (Fixed Bottom) ---
if prompt := st.chat_input("Décrivez le problème..."):
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build Context
    v = st.session_state.vehicle_info
    context = (
        f"CONTEXTE VÉHICULE:\n"
        f"- Modèle: {v.get('model')}\n"
        f"- Année: {v.get('year')}\n"
        f"- Moteur: {v.get('engine')}\n"
        f"- Km: {v.get('km')}\n"
        f"- Carburant: {v.get('fuel')}\n"
        f"- Code Défaut: {v.get('code')}\n\n"
        f"DEMANDE UTILISATEUR: {prompt}"
    )

    # AI Response
    if client:
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-preview-02-05:free",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                stream=True
            )
            response = st.write_stream(stream)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
