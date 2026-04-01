import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from io import BytesIO
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="BGE Bretagne - Saisie & Dashboard", layout="wide")

# Initialisation de la connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Initialisation des variables de session ---
if 'form_data' not in st.session_state:
    st.session_state.form_data = []
if 'list_generated' not in st.session_state:
    st.session_state.list_generated = False

st.title("🚀 Gestion des Bénéficiaires - BGE Bretagne")

# Création des onglets
tab_saisie, tab_stats = st.tabs(["📝 Saisie de masse", "📊 Statistiques"])

# --- ONGLET 1 : SAISIE DE MASSE ---
with tab_saisie:
    st.header("Saisie des présences et orientations")
    
    # Zone de texte pour coller la liste
    raw_names = st.text_area(
        "Collez ici la liste des 'Nom Prénom' (un par ligne)",
        placeholder="MARTIN Jean\nDUBOIS Marie...",
        height=150
    )
    
    if st.button("Générer le formulaire"):
        if raw_names.strip():
            # Nettoyage et création de la liste de bénéficiaires
            names_list = [name.strip() for name in raw_names.split('\n') if name.strip()]
            st.session_state.form_data = []
            for name in names_list:
                st.session_state.form_data.append({
                    "Date": datetime.now().strftime("%d/%m/%Y"),
                    "Bénéficiaire": name,
                    "État": "Présent",
                    "Conseiller": "",
                    "Orientations": [],
                    "Précisions Externe": ""
                })
            st.session_state.list_generated = True
        else:
            st.warning("Veuillez coller au moins un nom.")

    # Affichage du formulaire dynamique
    if st.session_state.list_generated:
        st.divider()
        with st.form("form_global"):
            for i, entry in enumerate(st.session_state.form_data):
                st.subheader(f"👤 {entry['Bénéficiaire']}")
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    st.session_state.form_data[i]['État'] = st.radio(
                        f"État ({entry['Bénéficiaire']})", 
                        ["Présent", "Absent"], 
                        key=f"etat_{i}",
                        horizontal=True
                    )
                
                with col2:
                    st.session_state.form_data[i]['Conseiller'] = st.text_input(
                        "Conseiller", 
                        key=f"cons_{i}"
                    )
                
                with col3:
                    options = ["Pass Création", "Créascope", "Ti-brsa", "Creer sa Réussite", "Agefiph", "Formation BGE", "Externe"]
                    selected = st.multiselect(
                        "Orientations", 
                        options, 
                        key=f"orient_{i}"
                    )
                    st.session_state.form_data[i]['Orientations'] = selected
                    
                    if "Externe" in selected:
                        st.session_state.form_data[i]['Précisions Externe'] = st.text_input(
                            "Détails orientation externe", 
                            key=f"ext_{i}"
                        )
                st.divider()

            # Boutons d'action
            col_save, col_export = st.columns(2)
            
            with col_save:
                submit = st.form_submit_button("📤 Envoyer vers Google Sheets")
                if submit:
                    try:
                        # Transformation des données pour l'envoi
                        df_to_send = pd.DataFrame(st.session_state.form_data)
                        # On transforme la liste des orientations en chaîne de caractères
                        df_to_send['Orientations'] = df_to_send['Orientations'].apply(lambda x: ", ".join(x))
                        
                        # Récupération des données existantes
                        existing_data = conn.read()
                        updated_df = pd.concat([existing_data, df_to_send], ignore_index=True)
                        
                        # Mise à jour
                        conn.update(data=updated_df)
                        st.success("Données enregistrées avec succès dans Google Sheets !")
                    except Exception as e:
                        st.error(f"Erreur lors de l'envoi : {e}")

        # Export Excel (Hors du formulaire st.form pour éviter les bugs de téléchargement)
        df_export = pd.DataFrame(st.session_state.form_data)
        df_export['Orientations'] = df_export['Orientations'].apply(lambda x: ", ".join(x))
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Saisie')
        
        st.download_button(
            label="📥 Exporter la session actuelle en Excel",
            data=output.getvalue(),
            file_name=f"export_bge_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- ONGLET 2 : STATISTIQUES ---
with tab_stats:
    st.header("Tableau de Bord")
    
    # Lecture des données complètes
    try:
        df_stats = conn.read()
        
        if not df_stats.empty:
            # Métriques rapides
            total = len(df_stats)
            presences = len(df_stats[df_stats['État'] == "Présent"])
            taux_presence = (presences / total) * 100 if total > 0 else 0
            
            m1, m2 = st.columns(2)
            m1.metric("Total Bénéficiaires", total)
            m2.metric("Taux de Présence Global", f"{taux_presence:.1f}%")
            
            # Graphique des orientations
            st.subheader("Répartition des Orientations")
            # On sépare les orientations qui sont stockées en chaînes séparées par des virgules
            all_orientations = []
            for row in df_stats['Orientations'].dropna():
                if isinstance(row, str):
                    all_orientations.extend([x.strip() for x in row.split(',') if x.strip()])
            
            if all_orientations:
                orient_counts = pd.Series(all_orientations).value_counts()
                st.bar_chart(orient_counts)
            else:
                st.info("Aucune donnée d'orientation disponible pour le graphique.")
                
            # Affichage du tableau brut
            with st.expander("Voir les données brutes"):
                st.dataframe(df_stats)
        else:
            st.info("Le Google Sheet est vide pour le moment.")
            
    except Exception as e:
        st.error(f"Impossible de charger les statistiques : {e}")

# --- CSS Personnalisé ---
st.markdown("""
    <style>
    .stForm {
        border: none;
        padding: 0;
    }
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border-top: 2px solid #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)
