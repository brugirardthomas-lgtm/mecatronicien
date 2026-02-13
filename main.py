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
st.set_page_config(page_title="Cadre Diagnosticien", page_icon="🔧", layout="wide")

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
    # Cast explicite pour le linter
    s = str(content)
    # Linter workaround: Slicing explicit
    if len(s) > length:
        return s[:length] # type: ignore
    return s

def transcribe_audio(audio_bytes):
    """Transcription audio via Google Speech Recognition."""
    r = sr.Recognizer()
    text = ""
    # Création d'un fichier temporaire pour le traitement
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_audio.write(audio_bytes)
        tmp_audio_path = tmp_audio.name

    try:
        with sr.AudioFile(tmp_audio_path) as source:
            # Enregistrement et nettoyage du bruit ambiant
            r.adjust_for_ambient_noise(source)
            audio_data = r.record(source)
            # Reconnaissance (langue française)
            text = r.recognize_google(audio_data, language="fr-FR")
    except sr.UnknownValueError:
        pass # Audio non compris, on ignore silencieusement ou on log
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
    # On utilise un modèle multimodal performant
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

    st.title("Diagnosticien Expert KTS (Multimodal & Vocal) 🔧")

    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    
    # State pour l'audio processed pour éviter les boucles
    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None
    
    # State pour TTS autoplay
    if "last_tts_audio" not in st.session_state:
        st.session_state.last_tts_audio = None

    # --- Zone Info Véhicule (sidebar enroulable) ---
    st.sidebar.markdown("### 🚗 Véhicule")
    
    with st.sidebar.container():
        voiture_modele = st.text_input("Modèle", placeholder="Ex: Renault Clio 4", key="v_model")
        annee = st.number_input("Année", 1980, 2025, 2015, key="v_year")
        kilometrage = st.number_input("Km", 0, step=1000, value=100000, key="v_km")
        code_defaut = st.text_input("Code Défaut / Symptôme", placeholder="Ex: P0087", key="v_fault")
        carburant = st.selectbox("Carburant", ["Diesel", "Essence", "Hybride", "Électrique"], key="v_fuel")
        code_moteur = st.text_input("Code Moteur", placeholder="Ex: K9K", key="v_engine")
    
    st.sidebar.info("Remplissez les infos véhicule ici.")

    # --- Gestion de l'audio TTS (Autoplay) ---
    if st.session_state.last_tts_audio:
        st.audio(st.session_state.last_tts_audio, format="audio/mp3", autoplay=True)

    # --- Zone Journal du Diagnostic (Historique) ---
    st.subheader("📝 Journal du Diagnostic")
    
    # Container pour l'historique scrollable
    chat_container = st.container(height=600)
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    if isinstance(msg["content"], list):
                        for content_part in msg["content"]:
                            if content_part["type"] == "text":
                                st.markdown(content_part["text"])
                            elif content_part["type"] == "image_url":
                                st.image(content_part["image_url"]["url"], width=200, caption="Image analysée")
                    else:
                        st.markdown(msg["content"])

    st.markdown("---")

    # --- Ergononomie Mobile : Espacement ---
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Zone de Saisie & Outils (Commune) ---
    st.subheader("🔧 Outils de Diagnostic")
    
    # Layout 3 colonnes pour les outils
    col_vision, col_doc, col_vocal = st.columns(3)
    
    # Outil 1 : Vision (Caméra Directe)
    with col_vision:
        st.markdown("##### 📷 Photo")
        # Remplacement par st.camera_input pour mobile
        uploaded_image = st.camera_input("Prendre photo", label_visibility="collapsed")
        if uploaded_image:
            st.success("✅ Prête")
        else:
            st.info("Ouvrir Caméra")

    # Outil 2 : Doc
    with col_doc:
        st.markdown("##### 📄 PDF")
        uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded_pdf:
            st.success("✅ Prêt")
        else:
            st.info("Ajouter PDF")

    # Outil 3 : Vocal
    with col_vocal:
        st.markdown("##### 🎤 Audio")
        audio_input = st.audio_input("Vocal", label_visibility="collapsed")
        
        # Logique de transcription immédiate
        processed_audio_text = None
        if audio_input is not None:
            current_audio_bytes = audio_input.getvalue()
            current_audio_id = hash(current_audio_bytes)
            st.success("✅ Prêt")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Actions Contextuelles ---
    
    # Cas 1 : Le diagnostic n'a pas commencé
    if not st.session_state.diagnostic_started:
        
        st.markdown("##### 📝 Observations & Lancement")
        symptomes_client = st.text_area(
            "Observations du client / Symptômes ressentis", 
            placeholder="Ex: Perte de puissance, bruit suspect...",
            height=100
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        # Bouton Lancer LARGE (Mobile)
        start_button = st.button("🚀 LANCER LE DIAGNOSTIC", type="primary", use_container_width=True)

        if start_button:
            if not voiture_modele or not code_defaut:
                st.error("⚠️ Merci de remplir le Modèle et le Code Défaut dans la barre latérale.")
            else:
                # 1. Transcription Audio si présent
                audio_text = ""
                if audio_input:
                     with st.spinner("Transcription audio..."):
                        audio_text = transcribe_audio(audio_input.getvalue())
                
                # 2. Construction du Contexte
                contexte_km = "Attention: Fort kilométrage." if kilometrage > 200000 else ""
                
                pdf_text: str = process_pdf(uploaded_pdf)
                contexte_doc = ""
                if pdf_text and len(pdf_text) > 0:
                    truncated_text = safe_truncate(pdf_text, 30000)
                    contexte_doc = f"\n\n[CONTEXTE DOCUMENTAIRE PDF] :\n{truncated_text}..."
                
                # Fusion des observations
                obs_finales = symptomes_client
                if audio_text:
                    obs_finales += f" [VOCAL TRANSCRIT: {audio_text}]"

                initial_text = f"""
                NOUVEAU CAS :
                Véhicule : {voiture_modele} ({annee}) - {carburant}
                Moteur : {code_moteur}
                Kilométrage : {kilometrage} km
                Problème signalé (Code/Défaut) : {code_defaut}
                Symptômes ressentis / Observations : {obs_finales}
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
                
                with st.spinner("🧠 Analyse Expert en cours..."):
                    response = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    audio_file = text_to_speech(response)
                    if audio_file:
                        st.session_state.last_tts_audio = audio_file
                        
                    st.rerun()

    # Cas 2 : Diagnostic en cours
    else:
        st.markdown("##### 💬 Réponse au Test")
        
        observation = st.text_input("Résultat du test / Observation", key="user_input_running")
        
        st.markdown("<br>", unsafe_allow_html=True)

        col_send, col_new = st.columns([3, 1])
        with col_send:
            # Bouton Envoyer LARGE (Mobile)
            send_clicked = st.button("📨 ENVOYER LA RÉPONSE", type="primary", use_container_width=True)
        with col_new:
            # Bouton Nouveau LARGE
            new_diag = st.button("🔄 Nouveau", use_container_width=True)
        
        if new_diag:
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.session_state.diagnostic_started = False
            st.session_state.last_audio_id = None
            st.session_state.last_tts_audio = None
            st.rerun()

        if send_clicked:
            # 1. Transcription Audio si présent
            audio_text = ""
            if audio_input:
                with st.spinner("Transcription audio..."):
                    audio_text = transcribe_audio(audio_input.getvalue())

            # Priorité : Audio > Texte saisi > Rien
            input_text = observation
            if audio_text:
                input_text += f" [VOCAL TRANSCRIT: {audio_text}]"
            
            # On envoie seulement s'il y a du contenu
            if input_text or uploaded_image or uploaded_pdf:
                user_message_content: list[dict[str, Any]] = []
                
                text_content = input_text if input_text else "Voici un complément d'information."
                
                pdf_text: str = process_pdf(uploaded_pdf)
                if pdf_text and len(pdf_text) > 0:
                    truncated_text = safe_truncate(pdf_text, 20000)
                    text_content += f"\n\n[NOUVELLE DOC PDF FOURNIE] :\n{truncated_text}..."
                
                user_message_content.append({"type": "text", "text": text_content})
                
                image_url = process_image(uploaded_image)
                if image_url:
                    user_message_content.append({
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    })
                
                st.session_state.messages.append({"role": "user", "content": user_message_content}) # type: ignore
                
                with st.spinner("🧠 Analyse des nouvelles données..."):
                    response = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    audio_file = text_to_speech(response)
                    if audio_file:
                        st.session_state.last_tts_audio = audio_file
                        
                    st.rerun()
            else:
                st.warning("⚠️ Veuillez saisir une réponse, parler, ou ajouter une photo/doc.")

if __name__ == "__main__":
    main()