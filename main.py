import os

# Configuration de la page
st.set_page_config(page_title="Expert KTS", page_icon="🔧", layout="centered", initial_sidebar_state="collapsed")
st.set_page_config(page_title="IAMECA - Expert", page_icon="🔧", layout="centered", initial_sidebar_state="collapsed")

# --- CSS GLOBAL STYLE (STITCH DESIGN) ---
# --- CSS GLOBAL STYLE (STITCH DESIGN & IAMECA BRANDING) ---
st.markdown("""
<style>
    /* Import Inter Font */
@@ -115,36 +115,74 @@
        border: 1px solid var(--input-border) !important;
    }

    /* CHAT BUBBLES */
    /* WHATSAPP STYLE CHAT BUBBLES */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 10px 0 !important;
    }
    
    /* User Message */
    div[data-testid="stChatMessage"]:nth-child(even) {
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
    
    /* AI Message */
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
@@ -284,8 +322,9 @@ def main():
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False

    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None
    # --- AUDIO STATE FIX (BOUCLE INFINIE) ---
    if "last_processed_audio_id" not in st.session_state:
        st.session_state.last_processed_audio_id = None

    if "last_tts_audio" not in st.session_state:
        st.session_state.last_tts_audio = None
@@ -309,7 +348,13 @@ def main():
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h1 style='font-size: 28px; margin-bottom: 4px;'>Nouveau Diagnostic</h1>", unsafe_allow_html=True)
        # BRANDING IAMECA
        st.markdown("""
        <h1 style='font-size: 32px; margin-bottom: 15px; font-weight: 800;'>
            <span style='color:#3B82F6'>IA</span><span style='color:#FFFFFF'>MECA</span>
        </h1>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='color: #A0A0A0; font-size: 14px; margin-bottom: 24px;'>Remplissez les données du véhicule pour lancer l'analyse.</p>", unsafe_allow_html=True)

        # --- CARTE 1: VÉHICULE ---
@@ -377,6 +422,8 @@ def main():
                if audio_input:
                     with st.spinner("Transcription audio..."):
                        audio_text = transcribe_audio(audio_input.getvalue())
                        # Mark audio as processed for initial setup too
                        st.session_state.last_processed_audio_id = hash(audio_input.getvalue())

                contexte_km = "Attention: Fort kilométrage." if st.session_state.v_km > 200000 else ""

@@ -436,7 +483,7 @@ def main():
        <div style="position: sticky; top: 0; z-index: 99; background: #121212; padding: 10px 0; border-bottom: 1px solid #2C2C2E; display: flex; justify-content: space-between; align-items: center;">
             <button style="background:none; border:none; color: white;">🔙</button>
             <div style="text-align: center;">
                 <h3 style="margin: 0; font-size: 16px; color: white;">{header_title}</h3>
                 <h3 style="margin: 0; font-size: 16px; color: white; font-weight: 600;">{header_title}</h3>
                 <div style="color: #22C55E; font-size: 12px; display: flex; align-items: center; gap: 4px; justify-content: center;">
                    <span style="display:inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22C55E;"></span> En ligne
                 </div>
@@ -451,45 +498,59 @@ def main():
            st.audio(st.session_state.last_tts_audio, format="audio/mp3", autoplay=True)

        # CHAT HISTORY
        chat_container = st.container(height=500)
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] != "system":
                    with st.chat_message(msg["role"], avatar="🔧" if msg["role"] == "user" else "🤖"):
                        if isinstance(msg["content"], list):
                            for content_part in msg["content"]:
                                if content_part["type"] == "text":
                                    st.markdown(content_part["text"])
                                elif content_part["type"] == "image_url":
                                    st.image(content_part["image_url"]["url"], width=200)
                        else:
                            st.markdown(msg["content"])
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

        st.markdown("<hr style='border-color: #2C2C2E; margin: 10px 0;'>", unsafe_allow_html=True)
        # Spacer for sticky footer (ensure content scrolls above inputs)
        st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

        # INPUT AREA (Sticky-like)
        # INPUT AREA (Sticky Tools + Chat Input)

        # Tools Row
        c_tools_1, c_tools_2, c_tools_3 = st.columns(3)
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

            # 1. Processing Inputs
            input_text = observation if observation else ""
            
            audio_txt = ""
            if voc_input:
            
            # --- AUDIO LOOP FIX IMPLEMENTATION ---
            current_audio_id = hash(voc_input.getvalue()) if voc_input else None
            
            if voc_input and current_audio_id != st.session_state.last_processed_audio_id:
                with st.spinner("Transcription..."):
                    audio_txt = transcribe_audio(voc_input.getvalue())
                st.session_state.last_processed_audio_id = current_audio_id

            if audio_txt:
                input_text += f" [VOCAL TRANSCRIT: {audio_txt}]"
@@ -514,7 +575,7 @@ def main():

                st.session_state.messages.append({"role": "user", "content": user_content}) # type: ignore

                with st.spinner("Analyse Expert..."):
                with st.spinner("Analyse IAMECA..."):
                    resp = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": resp})

@@ -524,11 +585,5 @@ def main():

                    st.rerun()

        # START OVER BUTTON
        if st.button("🔄 Nouveau Cas"):
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.session_state.diagnostic_started = False
            st.rerun()

if __name__ == "__main__":
    main()