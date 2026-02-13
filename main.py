import streamlit as st
from openai import OpenAI
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MecaDiag Expert",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SYSTEM PROMPT ---
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

# --- CSS STYLING (Mobile Friendly / WhatsApp Style) ---
st.markdown("""
<style>
    /* VARIABLES */
    :root {
        --bg-color: #0f0c29;
        --chat-bg: #1e1e2e;
        --user-msg: #007aff;
        --assistant-msg: #2c2c2e;
        --text-color: #ffffff;
    }

    /* 1. Global Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        background-attachment: fixed;
        color: var(--text-color);
    }

    /* 2. Hide Sidebar & Header */
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    
    /* 3. Main Container Spacing (Mobile Optimized) */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 8rem; /* Space for fixed chat input */
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }

    /* 4. Glass Expander (Vehicle Config) */
    .streamlit-expanderHeader {
        background: rgba(30, 35, 41, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        backdrop-filter: blur(10px);
    }
    
    /* 5. Chat Bubbles (Rounded iMessage Style) */
    .stChatMessage {
        background: transparent;
        border: none;
        padding: 0;
        margin-bottom: 10px;
    }
    
    /* User Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        flex-direction: row-reverse;
        text-align: right;
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stMarkdown {
        background: var(--user-msg);
        color: white;
        border-radius: 20px 20px 4px 20px;
        padding: 10px 15px;
        display: inline-block;
        max-width: 85%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }

    /* Assistant Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) .stMarkdown {
        background: var(--assistant-msg);
        color: white;
        border-radius: 20px 20px 20px 4px;
        padding: 10px 15px;
        display: inline-block;
        max-width: 85%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Hide default avatars for cleaner look if desired, or keep them */
    .stChatMessageAvatarUser, .stChatMessageAvatarAssistant {
        background-color: transparent !important; 
    }

    /* 6. Inputs & Selects */
    .stTextInput > div > div, .stSelectbox > div > div {
        background-color: rgba(38, 39, 48, 0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    /* 7. Floating Chat Input (Fixed Bottom) */
    .stChatInput {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 10px;
        background: rgba(15, 12, 41, 0.95);
        backdrop-filter: blur(20px);
        z-index: 1000;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    /* 8. Action Buttons (Camera/PDF) */
    .action-btn-container {
        display: flex;
        gap: 10px;
        margin-bottom: 5px;
        justify-content: flex-start;
        padding-left: 10px;
    }
    div.stButton > button {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 50% !important; /* Round buttons */
        width: 40px !important;
        height: 40px !important;
        padding: 0 !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vehicle_info" not in st.session_state:
    st.session_state.vehicle_info = {
        "model": "", "year": "", "fuel": "Diesel", 
        "km": "", "engine": "", "code": ""
    }
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False

# --- OPENAI CLIENT ---
def get_client():
    api_key = st.secrets.get("OPENROUTER_API_KEY")
    if not api_key:
        st.error("⚠️ Clé API non trouvée dans .streamlit/secrets.toml")
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

client = get_client()

# --- 1. CONFIGURATION VÉHICULE (Top Expander) ---
with st.expander("🚗 Configuration Véhicule", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.vehicle_info['model'] = st.text_input("Modèle", value=st.session_state.vehicle_info['model'], placeholder="Ex: Clio 4")
        st.session_state.vehicle_info['year'] = st.text_input("Année", value=st.session_state.vehicle_info['year'], placeholder="2015")
        st.session_state.vehicle_info['fuel'] = st.selectbox("Carburant", ["Diesel", "Essence", "Hybride", "Électrique"], index=["Diesel", "Essence", "Hybride", "Électrique"].index(st.session_state.vehicle_info['fuel']))
    with c2:
        st.session_state.vehicle_info['km'] = st.text_input("Km", value=st.session_state.vehicle_info['km'], placeholder="120000")
        st.session_state.vehicle_info['engine'] = st.text_input("Moteur", value=st.session_state.vehicle_info['engine'], placeholder="Ex: 1.5 dCi")
        st.session_state.vehicle_info['code'] = st.text_input("Code Défaut", value=st.session_state.vehicle_info['code'], placeholder="P0xxx")

# --- 2. CHAT HISTORY ---
# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 3. TOOLS & INPUT (Bottom) ---

# Optional Camera Input Area
if st.session_state.show_camera:
    with st.container():
        img = st.camera_input("Photo")
        if img:
            st.success("Photo capturée (simulation)")
            st.session_state.show_camera = False
            st.rerun()

# Tools Buttons (just above chat input)
# We use columns to place small buttons. 
# Note: Streamlit's layout limits sticky positioning of these without raw HTML/CSS hacks, 
# but we can place them right before the chat_input in the flow.
c_tools, _ = st.columns([2, 8])
with c_tools:
    c_cam, c_pdf = st.columns(2)
    with c_cam:
        if st.button("📷", help="Prendre une photo"):
            st.session_state.show_camera = not st.session_state.show_camera
            st.rerun()
    with c_pdf:
         # Hidden file uploader trick or just a button that opens one? 
         # St.file_uploader cannot be triggered by a button easily. 
         # We will toggle visibility of a file uploader.
         pass 

# If camera or pdf mode is not active, maybe show file uploader?
# For now, let's keep it simple as requested: "deux icônes discrètes"
# To make "📄" work, we might need a dedicated area.
# Let's simplify: Icon 📄 toggles a file uploader container.
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = False

# Re-render tools row to include logic
if st.session_state.show_uploader:
    uploaded_file = st.file_uploader("Fichier PDF", type="pdf")
    if uploaded_file:
        st.success("PDF chargé")

# --- 4. CHAT LOGIC ---
if prompt := st.chat_input("Décrivez le problème..."):
    if not prompt.strip():
        st.warning("Message vide.")
        st.stop()

    # Add User Message to State
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build Context
    v = st.session_state.vehicle_info
    vehicle_context = (
        f"VÉHICULE: {v['model']} {v['engine']} ({v['year']}), {v['km']}km, {v['fuel']}.\n"
        f"CODE DÉFAUT: {v['code']}.\n"
    )
    full_prompt = f"{vehicle_context}\nDEMANDE: {prompt}"

    # API Call
    if client:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                completion = client.chat.completions.create(
                    model="google/gemini-2.0-flash-lite-001",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": full_prompt}
                    ],
                    stream=False
                )
                
                full_response = completion.choices[0].message.content
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_msg = f"❌ Erreur API: {str(e)}"
                message_placeholder.error(error_msg)
    else:
        st.error("Client API non initialisé.")
