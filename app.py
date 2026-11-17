import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(page_title="ÉCOLE VIGILANTE", page_icon="🏫", layout="wide")

st.title("🏫 ÉCOLE VIGILANTE")
st.markdown("### Cartographie et anticipation du risque de décrochage scolaire au Burkina Faso")
st.markdown("---")

# ==========================================
# 2. CHARGEMENT DES DONNÉES (Sécurisé)
# ==========================================
@st.cache_data
def charger_donnees():
    df = pd.read_csv("data/region-indicateurs.csv")
    df['region'] = df['region'].str.upper()
    return df

@st.cache_data
def charger_previsions():
    try:
        df_prev = pd.read_csv("data/previsions_2026.csv")
        df_prev['region'] = df_prev['region'].str.upper()
        return df_prev
    except FileNotFoundError:
        return None

@st.cache_data
def charger_historique():
    try:
        # On charge l'historique pour le graphique de prévision
        df_hist = pd.read_csv("data/historique_achevement.csv")
        df_hist['region'] = df_hist['region'].str.upper()
        df_hist = df_hist.groupby(['region', 'annee'])['taux_achevement'].mean().reset_index()
        return df_hist
    except FileNotFoundError:
        return None

try:
    df = charger_donnees()
    df_prev = charger_previsions()
    df_hist = charger_historique()
except FileNotFoundError:
    st.error("❌ Fichier 'region-indicateurs.csv' introuvable. Vérifiez le dossier 'data/'.")
    st.stop()

# ==========================================
# 3. BARRE LATÉRALE (Filtres)
# ==========================================
st.sidebar.header("Filtres")
regions_dispos = ["Toutes les régions"] + sorted(df['region'].unique().tolist())
region_selectionnee = st.sidebar.selectbox("Sélectionner une région", regions_dispos)

# ==========================================
# 4. INDICATEURS CLÉS (KPIs)
# ==========================================
st.subheader("📊 Vue d'ensemble")
col1, col2, col3, col4 = st.columns(4)

nb_regions_critiques = len(df[df['Niveau_Alerte'] == '🔴 Alerte Critique'])
taux_moyen = df['taux_achevement_2025'].mean()
perte_moy_ecoles = df['perte_ecoles'].mean() * 100

col1.metric("Régions en Alerte Critique", nb_regions_critiques)
col2.metric("Taux d'achèvement national", f"{taux_moyen:.1f} %")
col3.metric("Perte moyenne d'écoles", f"{perte_moy_ecoles:.1f} %")
col4.metric("Indice de Risque Moyen (IRD)", f"{df['IRD'].mean():.1f} / 100")

st.markdown("---")

# ==========================================
# 5. LA CARTE INTERACTIVE (Version ultime)
# ==========================================
st.subheader("🗺️ Cartographie du Risque de Décrochage (IRD)")

try:
    with open("data/burkina_regions.json", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    
    # 1. On crée une liste des noms EXACTS contenus dans le fichier JSON
    noms_geojson = [feature['properties']['NAME_1'] for feature in geojson_data['features']]
    
    # 2. Dictionnaire de correspondance forcé (CSV -> JSON)
    # On cherche comment le JSON a bien pu orthographier "Hauts-Bassins"
    def trouver_nom_json(region_csv):
        if region_csv == "HAUTS-BASSINS":
            # On cherche dans le JSON un nom qui contient "Haut" et "Bassin"
            for nom in noms_geojson:
                if "haut" in nom.lower() and "bassin" in nom.lower():
                    return nom
        elif region_csv == "BOUCLE DU MOUHOUN":
            for nom in noms_geojson:
                if "boucle" in nom.lower():
                    return nom
        elif region_csv == "PLATEAU CENTRAL":
            for nom in noms_geojson:
                if "plateau" in nom.lower():
                    return nom
        
        # Pour toutes les autres régions, on applique le nettoyage classique
        for nom in noms_geojson:
            if str(region_csv).replace("-", "").replace(" ", "").lower() == str(nom).replace("-", "").replace(" ", "").lower():
                return nom
        return None

    # 3. On applique cette recherche intelligente à nos données
    df['region_match'] = df['region'].apply(trouver_nom_json)
    
    # 4. On génère la carte
    fig_carte = px.choropleth(
        df, 
        geojson=geojson_data, 
        locations="region_match", 
        featureidkey="properties.NAME_1",
        color="IRD", 
        color_continuous_scale="Reds", 
        range_color=(0, 100), 
        hover_name="region",
        hover_data={"taux_achevement_2025": ":.1f", "perte_ecoles": ":.2f", "IRD": ":.1f"},
        labels={"IRD": "Indice de Risque"}
    )
    fig_carte.update_geos(fitbounds="locations", visible=False)
    fig_carte.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
    st.plotly_chart(fig_carte, use_container_width=True, config={'displayModeBar': False})
    
except FileNotFoundError:
    st.error("❌ Fichier 'burkina_regions.json' introuvable.")
    
# ==========================================
# 6. CLASSEMENT ET FICHE D'ACTION (Mise en page verticale)
# ==========================================

# --- 6.1 LE CLASSEMENT (Sur toute la largeur) ---
st.subheader("📉 Classement des régions par Indice de Risque")
df_trié = df.sort_values('IRD', ascending=True)

fig_bar = px.bar(
    df_trié, x='IRD', y='region', orientation='h',
    color='IRD', color_continuous_scale="Reds", text='IRD'
)
fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside')
fig_bar.update_layout(
    showlegend=False, 
    xaxis_title="Score IRD (0 à 100)", 
    yaxis_title="",
    height=450, # On donne un peu plus de hauteur pour que ce soit aéré
    margin=dict(l=20, r=20, t=20, b=20)
)
st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")

# --- 6.2 LA FICHE D'ACTION (En dessous) ---
st.subheader("⚠️ Fiche d'action pour le décideur")

if region_selectionnee != "Toutes les régions":
    data_region = df[df['region'] == region_selectionnee].iloc[0]
    
    # Bandeau d'information
    st.info(f"**Région sélectionnée : {data_region['region']}** | Statut : **{data_region['Niveau_Alerte']}**")
    
    # 1. Les Métriques (sur 3 colonnes pour gagner de la place)
    c1, c2, c3 = st.columns(3)
    c1.write(f"🔹 **Indice de Risque (IRD) :** {data_region['IRD']:.1f} / 100")
    c2.write(f"🔹 **Taux d'achèvement :** {data_region['taux_achevement_2025']:.1f} %")
    c3.write(f"🔹 **Variation des écoles :** {data_region['perte_ecoles']*100:.1f} %")
    
    st.write("---")
    
    # 2. Diagnostic automatique
    st.markdown("**💡 Diagnostic automatique :**")
    presco = data_region.get('tbs_prescolaire', data_region.get('tbs_prescolaire_2025', 10))
    
    if data_region['taux_achevement_2025'] < 30:
        st.error("🚨 **Urgence absolue** : Le taux d'achèvement est critique. Risque d'effondrement du système éducatif.")
    elif data_region['perte_ecoles'] < -0.3:
        st.warning("⚠️ **Alerte sécuritaire** : Perte massive d'infrastructures. Nécessité d'écoles mobiles.")
    elif presco < 3:
        st.info("ℹ️ **Levier de prévention** : Le préscolaire est très faible. Investir dans la petite enfance.")
    else:
        st.success("✅ **Situation sous contrôle** : Maintenir les efforts et surveiller les indicateurs.")

    # 3. LE RADAR CHART (Centré avec marges corrigées)
    st.markdown("<h5 style='text-align: center; margin-top: 30px;'>🕸️ Profil des vulnérabilités</h5>", unsafe_allow_html=True)
    
    categories = ['Achèvement', 'Écoles', 'Ruralité', 'TBS', 'Préscolaire']
    score_ach = data_region.get('score_achevement', 0) * 100
    score_eco = data_region.get('score_ecoles', 0) * 100
    score_rur = data_region.get('score_rural', 0) * 100
    score_tbs = data_region.get('score_tbs', 0) * 100
    score_pre = data_region.get('score_prescolaire', 0) * 100
    valeurs = [score_ach, score_eco, score_rur, score_tbs, score_pre]
    
    categories_plot = categories + [categories[0]]
    valeurs_plot = valeurs + [valeurs[0]]

    # On utilise des colonnes vides autour pour forcer le radar à rester au centre
    _, col_centre, _ = st.columns([1, 2, 1])
    
    with col_centre:
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=valeurs_plot, theta=categories_plot, fill='toself', 
            fillcolor='rgba(255, 0, 0, 0.3)', line_color='red',
            hovertemplate="%{theta} : %{r:.0f} / 100<extra></extra>" 
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False, 
            # 🚨 AUGMENTATION DES MARGES POUR ÉVITER QUE LE TEXTE SOIT COUPÉ
            margin=dict(l=80, r=80, t=40, b=40), 
            height=350
        )
        st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

        # 4. Facteurs de vulnérabilité détaillés (Explication dynamique)
    st.markdown("**🔍 Facteurs de vulnérabilité détaillés (classés par risque) :**")
    
    # Fonction pour générer le texte selon le score
    def get_explication(axe, score):
        # 🌟 CAS SPÉCIAL : SCORE DE 0 (Aucun risque)
        if score == 0:
            niveau = "AUCUN RISQUE 🌟"
            phrase = {
                'Achèvement': "Situation optimale, aucun risque d'abandon détecté.",
                'Écoles': "Aucune perte d'école enregistrée, le réseau est parfaitement stable.",
                'Ruralité': "Vulnérabilité rurale inexistante (zone très fortement urbanisée).",
                'TBS': "Couverture scolaire parfaite, aucun enfant n'est laissé de côté.",
                'Préscolaire': "Excellente couverture préscolaire, aucun déficit."
            }[axe]
            
        elif score >= 70:
            niveau = "CRITIQUE 🚨"
            phrase = {
                'Achèvement': "Effondrement du système éducatif, abandon massif.",
                'Écoles': "Destruction ou fermeture massive des infrastructures.",
                'Ruralité': "Isolement total des zones rurales.",
                'TBS': "Très faible scolarisation, la majorité des enfants est hors du système.",
                'Préscolaire': "Absence quasi-totale de préparation de la petite enfance."
            }[axe]
            
        elif score >= 50:
            niveau = "ÉLEVÉ ⚠️"
            phrase = {
                'Achèvement': "Fort taux d'abandon avant la fin du primaire.",
                'Écoles': "Perte importante d'écoles, probablement liée à l'insécurité.",
                'Ruralité': "Forte concentration des élèves dans des zones rurales difficiles d'accès.",
                'TBS': "Couverture scolaire insuffisante pour la population cible.",
                'Préscolaire': "Manque important d'écoles maternelles."
            }[axe]
            
        elif score >= 30:
            niveau = "MODÉRÉ 🟡"
            phrase = {
                'Achèvement': "Quelques difficultés de rétention des élèves.",
                'Écoles': "Légère baisse du nombre d'écoles.",
                'Ruralité': "Proportion rurale notable.",
                'TBS': "Scolarisation partielle.",
                'Préscolaire': "Déficit de places au préscolaire."
            }[axe]
            
        else: # Score entre 1 et 29
            niveau = "FAIBLE ✅"
            phrase = {
                'Achèvement': "Bonne rétention, la majorité des élèves termine le primaire.",
                'Écoles': "Réseau d'écoles stable ou en croissance.",
                'Ruralité': "Faible vulnérabilité liée au milieu rural.",
                'TBS': "Bonne couverture scolaire.",
                'Préscolaire': "Accès au préscolaire relativement assuré."
            }[axe]
            
        return f"**{axe}** (Score {score:.0f}/100 - {niveau}) : {phrase}"
    
    # On trie les scores du plus grand au plus petit
    scores = list(zip(categories, valeurs))
    scores_tries = sorted(scores, key=lambda x: x[1], reverse=True)
    
    # On génère le texte pour TOUS les axes (même ceux à faible risque)
    texte_diagnostic = ""
    for axe, score in scores_tries:
        texte_diagnostic += f"* {get_explication(axe, score)}\n"
    
    # On affiche le bloc de texte
    st.warning(texte_diagnostic)

else:
    st.info("👈 Sélectionnez une région dans le menu de gauche pour voir sa fiche d'action et son profil de vulnérabilité.")
# ==========================================
# 7. 🔮 SECTION PRÉVISIONS 2026
# ==========================================
st.subheader("🔮 Anticipation : Que va-t-il se passer en 2026 ?")

if df_prev is not None:
    fig_prev = go.Figure()
    
    # 1. Tracer TOUTES les régions en gris clair (si on a l'historique)
    if df_hist is not None:
        for region in df_hist['region'].unique():
            if region not in ['SAHEL', 'EST']:
                hist_region = df_hist[df_hist['region'] == region]
                fig_prev.add_trace(go.Scatter(
                    x=hist_region['annee'], y=hist_region['taux_achevement'],
                    mode='lines', line=dict(color='lightgrey', width=1), 
                    showlegend=False, hoverinfo='skip'
                ))
    
    # 2. Tracer le SAHEL et L'EST avec leur historique complet (en rouge)
    for region_critique in ['SAHEL', 'EST']:
        # Historique (si dispo)
        if df_hist is not None:
            hist_region = df_hist[df_hist['region'] == region_critique]
            fig_prev.add_trace(go.Scatter(
                x=hist_region['annee'], y=hist_region['taux_achevement'],
                mode='lines+markers', name=f"{region_critique} (Historique)",
                line=dict(color='red', width=3)
            ))
        
        # Point de prévision 2026
        prev_region = df_prev[df_prev['region'] == region_critique]
        if not prev_region.empty:
            fig_prev.add_trace(go.Scatter(
                x=[2025, 2026], 
                y=[prev_region['taux_2025'].values[0], prev_region['prevision_2026'].values[0]],
                mode='lines+markers', name=f"{region_critique} (Prévision)",
                line=dict(color='red', width=3, dash='dash'), marker=dict(symbol='x', size=10)
            ))

    # 3. Ajouter le seuil critique
    fig_prev.add_hline(y=30, line_dash="dot", line_color="black", 
                       annotation_text="Seuil critique (30%)", annotation_position="bottom right")

    fig_prev.update_layout(
        title="Projection : Le Sahel et l'Est s'enfoncent sous le seuil critique",
        yaxis_title="Taux d'achèvement au primaire (%)",
        xaxis_title="Année",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    # On force l'axe X à afficher toutes les années de 2016 à 2026
    fig_prev.update_xaxes(tickmode='linear', tick0=2016, dtick=1)
    
    st.plotly_chart(fig_prev, use_container_width=True, config={'displayModeBar': False})
    
    st.error("🚨 **ALERTE MAJEURE** : Le graphique montre que même si toutes les autres régions stagnent, le **SAHEL** et l'**EST** sont sur une pente descendante qui va les écraser sous la barre des 15% en 2026. Une intervention d'urgence est requise.")

else:
    st.info("ℹ️ Les données de prévisions 2026 ne sont pas disponibles.")

# ==========================================
# 8. PIED DE PAGE
# ==========================================
st.markdown("---")
st.caption("Source : DGESS, Ministère de l'Éducation nationale du Burkina Faso (2015-2025).")
st.caption("« On ne développe pas, on se développe » — Joseph Ki-Zerbo.")