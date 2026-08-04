import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.set_page_config(
    page_title="Rio Location Simulator",
    page_icon="🇧🇷",
    layout="wide"
)

st.title("🇧🇷 Simulateur Stratégique & Foncier - Zona Sul (Rio)")
st.markdown("Pilote ton investissement et filtre les meilleures rues en temps réel.")

# Panneau Latéral (Sidebar)
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
st.sidebar.metric(label="Somme Postes Fixes (Vert)", value=f"{total_fixes:,.0f} R$")
st.sidebar.metric(label="Enveloppe Luvas Disponible (Bleu)", value=f"{orçamento_luvas_disponivel:,.0f} R$")

surface_cible = st.sidebar.slider("Surface Cible (m²)", min_value=30, max_value=120, value=55, step=5)

# Données de test / démo interconnectables (en attendant le lien direct Sheets cloud complet)
data_demo = {
    'Bairro': ['Copacabana', 'Ipanema', 'Leblon', 'Botafogo', 'Flamengo'],
    'Rua': ['Avenida Atlântica', 'Visconde de Pirajá', 'Ataulfo de Paiva', 'Praia de Botafogo', 'Rua do Catete'],
    'Custo_Luvas_m2_R$': [4500, 7800, 8500, 3200, 2800],
    'Aluguel_Mensal_m2_R$': [180, 250, 280, 140, 120],
    'Latitude': [-22.9646, -22.9838, -22.9858, -22.9515, -22.9348],
    'Longitude': [-43.1729, -43.2040, -43.2201, -43.1813, -43.1764]
}
df_base = pd.DataFrame(data_demo)

if not df_base.empty:
    df_base['Luvas_Total_Surface'] = df_base['Custo_Luvas_m2_R$'] * surface_cible
    df_base['Faisable'] = df_base['Luvas_Total_Surface'] <= orçamento_luvas_disponivel
    df_faisable = df_base[df_base['Faisable'] == True]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🏆 Top des Rues Recommandées (Dans ton budget)")
        if not df_faisable.empty:
            st.dataframe(df_faisable[['Bairro', 'Rua', 'Custo_Luvas_m2_R$', 'Luvas_Total_Surface']], use_container_width=True)
        else:
            st.warning("⚠️ Aucun bien ne rentre dans ton enveloppe de Luvas actuelle avec cette surface.")
            
    with col2:
        st.subheader("📊 Synthèse du Projet")
        st.metric("Rues éligibles", f"{len(df_faisable)} / {len(df_base)}")
        st.metric("Surface testée", f"{surface_cible} m²")

    st.subheader("🗺️ Carte Interactive des Opportunités (Zona Sul)")
    view_state = pdk.ViewState(latitude=-22.9711, longitude=-43.1822, zoom=12, pitch=30)
    df_base['color'] = df_base['Faisable'].apply(lambda x: [0, 200, 100, 180] if x else [200, 50, 50, 100])

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_base,
        get_position=["Longitude", "Latitude"],
        get_color="color",
        get_radius=200,
        pickable=True,
        auto_highlight=True,
    )

    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Quartier: {Bairro}\nRue: {Rua}\nLuvas Totales: {Luvas_Total_Surface} R$\nFaisable: {Faisable}"})
    st.pydeck_chart(r)
