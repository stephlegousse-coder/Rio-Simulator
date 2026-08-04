import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import ast

st.set_page_config(
    page_title="Rio Location Simulator",
    page_icon="🇧🇷",
    layout="wide"
)

st.title("🇧🇷 Simulateur Stratégique & Foncier - Zona Sul (Rio)")
st.markdown("Analyse des rues de la Zona Sul avec scoring piéton et cartographie interactive des tracés lissés.")

@st.cache_data
def load_data():
    try:
        # 1. Chargement de ton fichier de données principal
        df_main = pd.read_csv("database_rio.csv")
        df_main.columns = df_main.columns.str.strip()
        df_main['Rua'] = df_main['Rua'].astype(str).str.strip()
        df_main['Bairro'] = df_main['Bairro'].astype(str).str.strip()
        
        # 2. Chargement de ton fichier de géométrie mis à jour
        df_geo = pd.read_csv("Base_Data_Geo_rio.csv")
        df_geo.columns = df_geo.columns.str.strip()
        df_geo['Rua'] = df_geo['Rua'].astype(str).str.strip()
        df_geo['Bairro'] = df_geo['Bairro'].astype(str).str.strip()
        
        # Fonction simple pour décoder le JSON propre exporté depuis Colab
        def parse_path(val):
            if isinstance(val, str):
                try:
                    return ast.literal_eval(val)
                except:
                    return []
            return val if isinstance(val, list) else []

        if 'Path_Coordinates' in df_geo.columns:
            df_geo['path'] = df_geo['Path_Coordinates'].apply(parse_path)
        else:
            df_geo['path'] = [[[-43.1822, -22.9711], [-43.1830, -22.9720]]]

        # 3. Fusion propre sur Rua et Bairro
        df = pd.merge(df_main, df_geo[['Rua', 'Bairro', 'path']], on=['Rua', 'Bairro'], how='left')
        
        # Fallback de sécurité si un tracé venait à manquer
        default_path = [[-43.1905, -22.9645], [-43.1780, -22.9750]]
        df['path'] = df['path'].apply(lambda x: x if isinstance(x, list) and len(x) > 0 else default_path)
        
        return df
    except Exception as e:
        st.error(f"Erreur de chargement des fichiers : {e}")
        return pd.DataFrame()

df_base = load_data()

if not df_base.empty:
    st.sidebar.header("🛠️ Paramètres Financiers")
    user_apport = st.sidebar.number_input("Apport Total Disponible (R$)", value=700000, step=10000)

    st.sidebar.subheader("Postes Fixes (One-Shot)")
    c_travaux = st.sidebar.number_input("Custo Obras Fixo (R$)", value=170000, step=5000)
    c_equip = st.sidebar.number_input("Custo Equipamentos (R$)", value=190763, step=5000)
    c_mobilier = st.sidebar.number_input("Custo Mobiliário (R$)", value=20832, step=1000)
    c_marketing = st.sidebar.number_input("Custo Marketing (R$)", value=18500, step=1000)
    c_admin = st.sidebar.number_input("Custo Administrativo (R$)", value=18000, step=1000)
    c_secu = st.sidebar.number_input("Custo Segurança (R$)", value=17000, step=1000)
    c_ti = st.sidebar.number_input("Custo TI (R$)", value=5000, step=500)
    c_reserves = st.sidebar.number_input("Reserva de Emergência (R$)", value=93000, step=5000)

    total_fixes = c_travaux + c_equip + c_mobilier + c_marketing + c_admin + c_secu + c_ti + c_reserves
    orçamento_luvas_disponivel = user_apport - total_fixes

    st.sidebar.markdown("---")
    st.sidebar.metric(label="Enveloppe Luvas Disponible", value=f"{orçamento_luvas_disponivel:,.0f} R$")
    surface_cible = st.sidebar.slider("Surface Cible (m²)", min_value=30, max_value=120, value=55, step=5)

    # Calcul des coûts totaux basés sur la surface
    df_base['Luvas_Total'] = df_base['Custo_Luvas_m2_R$'] * surface_cible
    df_base['Aluguel_Mensal_Total'] = df_base['Aluguel_Mensal_m2_R$'] * surface_cible

    # Test de faisabilité
    df_base['Faisable'] = df_base['Luvas_Total'] <= orçamento_luvas_disponivel

    # Filtrage du Top 10
    df_faisable = df_base[df_base['Faisable'] == True].copy()
    df_faisable = df_faisable.sort_values(by=['Indice_Fluxo_Pedestres', 'Score_Global_Final'], ascending=False).reset_index(drop=True)
    df_faisable.index = df_faisable.index + 1

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🏆 Top 10 des Rues (Faisables & Triées par Flux Piéton)")
        if not df_faisable.empty:
            cols_to_show = ['Bairro', 'Rua', 'Indice_Fluxo_Pedestres', 'Luvas_Total', 'Aluguel_Mensal_Total', 'Score_Global_Final']
            st.dataframe(df_faisable[cols_to_show].head(10).style.format({
                'Indice_Fluxo_Pedestres': '{:,.0f}',
                'Luvas_Total': '{:,.0f} R$',
                'Aluguel_Mensal_Total': '{:,.0f} R$',
                'Score_Global_Final': '{:.1f}'
            }), use_container_width=True)
        else:
            st.warning("⚠️ Aucune rue ne respecte ton budget actuel avec cette surface.")

    with col2:
        st.subheader("📊 Synthèse Globale")
        st.metric("Rues éligibles au budget", f"{len(df_faisable)} / {len(df_base)}")
        st.metric("Surface testée", f"{surface_cible} m²")

    # Carte interactive PyDeck avec les tracés lissés (PathLayer)
    st.subheader("🗺️ Cartographie des Rues - Tracés Réels Lissés (Zona Sul)")
    
    def get_color(row):
        if not row['Faisable']:
            return [200, 50, 50, 140]  # Rouge transparent si non faisable
        score = row['Score_Global_Final']
        if score > 75:
            return [0, 220, 100, 230]  # Vert vif
        elif score > 50:
            return [50, 150, 250, 230] # Bleu
        elif score > 25:
            return [250, 200, 0, 230]  # Jaune
        else:
            return [200, 100, 50, 230] # Orange

    df_base['color'] = df_base.apply(get_color, axis=1)
    view_state = pdk.ViewState(latitude=-22.9711, longitude=-43.1822, zoom=13, pitch=30)

    layer = pdk.Layer(
        "PathLayer",
        data=df_base,
        get_path="path",
        get_color="color",
        width_scale=20,
        width_min_pixels=4,
        pickable=True,
        auto_highlight=True,
    )

    r = pdk.Deck(
        layers=[layer], 
        initial_view_state=view_state, 
        tooltip={
            "text": "Quartier: {Bairro}\nRue: {Rua}\nFlux Piétons: {Indice_Fluxo_Pedestres}\nScore Global: {Score_Global_Final}\nLuvas Total: {Luvas_Total:,.0f} R$\nLoyer: {Aluguel_Mensal_Total:,.0f} R$"
        }
    )
    st.pydeck_chart(r)
