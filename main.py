#!/usr/bin/env python3
import streamlit as st
from openai import OpenAI
from typing import Any
import base64
from PIL import Image
from pypdf import PdfReader
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

# System Prompt paramétré
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

def get_ai_response(client, messages):
    models = ["google/gemini-2.0-flash-lite-001", "meta-llama/llama-3.3-70b-instruct:free"]
    
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

    st.title("Diagnosticien Expert KTS 🔧")

    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    
    # Toggles pour les outils
    if "show_cam" not in st.session_state:
        st.session_state.show_cam = False
    if "show_pdf" not in st.session_state:
        st.session_state.show_pdf = False

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

    # --- Zone Journal du Diagnostic (Historique) ---
    st.subheader("📝 Journal du Diagnostic")
    
    # Container pour l'historique scrollable - HAUTEUR AGRANDIE 750px
    chat_container = st.container(height=750)
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

    # --- Barre d'Outils Compacte (Icones) ---
    col_tools, _ = st.columns([2, 10])
    with col_tools:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📷", help="Ouvrir/Fermer Caméra"):
                st.session_state.show_cam = not st.session_state.show_cam
                st.session_state.show_pdf = False # Close other tool
        with c2:
            if st.button("📄", help="Ouvrir/Fermer PDF"):
                st.session_state.show_pdf = not st.session_state.show_pdf
                st.session_state.show_cam = False # Close other tool

    # Zone d'affichage conditionnel des outils
    uploaded_image = None
    uploaded_pdf = None

    if st.session_state.show_cam:
        st.info("Mode Photo Activé")
        uploaded_image = st.camera_input("Prendre photo", label_visibility="collapsed")
    
    if st.session_state.show_pdf:
        st.info("Mode PDF Activé")
        uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")

    # --- Interface de Saisie (Contexte vs Chat) ---
    
    # Cas 1 : Le diagnostic n'a pas commencé
    if not st.session_state.diagnostic_started:
        
        st.markdown("##### 📝 Lancement")
        symptomes_client = st.text_area(
            "Observations du client / Symptômes", 
            placeholder="Ex: Perte de puissance...",
            height=70
        )
        
        start_button = st.button("🚀 LANCER", type="primary", use_container_width=True)

        if start_button:
            if not voiture_modele or not code_defaut:
                st.error("⚠️ Remplissez Modèle et Code Défaut (Sidebar).")
            else:
                contexte_km = "Attention: Fort kilométrage." if kilometrage > 200000 else ""
                
                pdf_text: str = process_pdf(uploaded_pdf)
                contexte_doc = ""
                if pdf_text and len(pdf_text) > 0:
                    truncated_text = safe_truncate(pdf_text, 30000)
                    contexte_doc = f"\n\n[CONTEXTE DOCUMENTAIRE PDF] :\n{truncated_text}..."
                
                obs_finales = symptomes_client

                initial_text = f"""
                NOUVEAU CAS :
                Véhicule : {voiture_modele} ({annee}) - {carburant}
                Moteur : {code_moteur}
                Kilométrage : {kilometrage} km
                Problème signalé (Code/Défaut) : {code_defaut}
                Symptômes ressentis / Observations : {obs_finales}
                {contexte_km}
                {contexte_doc}
                
                Analyse et propose le premier test.
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
                
                with st.spinner("🧠 Analyse..."):
                    response = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

    # Cas 2 : Diagnostic en cours
    else:
        observation = st.chat_input("Résultat du test / Observation...")
        
        # Bouton Nouveau Diagnostic (Petit et discret)
        if st.sidebar.button("🔄 Nouveau Diagnostic", use_container_width=True):
             st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
             st.session_state.diagnostic_started = False
             st.rerun()

        if observation:
            user_message_content: list[dict[str, Any]] = []
            
            text_content = observation
            
            pdf_text: str = process_pdf(uploaded_pdf)
            if pdf_text and len(pdf_text) > 0:
                truncated_text = safe_truncate(pdf_text, 20000)
                text_content += f"\n\n[NOUVELLE DOC PDF] :\n{truncated_text}..."
            
            user_message_content.append({"type": "text", "text": text_content})
            
            image_url = process_image(uploaded_image)
            if image_url:
                user_message_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
            
            st.session_state.messages.append({"role": "user", "content": user_message_content}) # type: ignore
            
            with st.spinner("🧠 Analyse..."):
                response = get_ai_response(client, st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

if __name__ == "__main__":
    main()