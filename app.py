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
st.markdown("Pilote ton investissement, ajuste tes coefficients d'attractivité et filtre les meilleures rues en temps réel.")

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
st.sidebar.metric(label="Somme Postes Fixes", value=f"{total_fixes:,.0f} R$")
st.sidebar.metric(label="Enveloppe Luvas Disponible", value=f"{orçamento_luvas_disponivel:,.0f} R$")

surface_cible = st.sidebar.slider("Surface Cible (m²)", min_value=30, max_value=120, value=55, step=5)

st.sidebar.markdown("---")
st.sidebar.header("⚖️ Coefficients d'Attractivité (Piétons)")
coef_pietons = st.sidebar.slider("Poids du flux piéton", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
coef_visibilité = st.sidebar.slider("Poids de la visibilité/emplacement", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

# Base de données enrichie (avec flux piétons fictifs pour l'exemple, connectable à ton Sheet)
data_demo = {
    'Bairro': ['Copacabana', 'Ipanema', 'Leblon', 'Botafogo', 'Flamengo'],
    'Rua': ['Avenida Atlântica', 'Visconde de Pirajá', 'Ataulfo de Paiva', 'Praia de Botafogo', 'Rua do Catete'],
    'Custo_Luvas_Total_R$': [247500, 429000, 467500, 176000, 154000],
    'Aluguel_Mensal_R$': [9900, 13750, 15400, 7700, 6600],
    'Flux_Pietons_Journalier': [15000, 12000, 11000, 8000, 6000],
    'Latitude': [-22.9646, -22.9838, -22.9858, -22.9515, -22.9348],
    'Longitude': [-43.1729, -43.2040, -43.2201, -43.1813, -43.1764]
}
df_base = pd.DataFrame(data_demo)

if not df_base.empty:
    # Calcul de la surface appliquée sur le Luvas Total de la base
    df_base['Luvas_Total_Surface'] = df_base['Custo_Luvas_Total_R$'] * (surface_cible / 55) # ajusté selon la surface
    df_base['Faisable'] = df_base['Luvas_Total_Surface'] <= orçamento_luvas_disponivel
    
    # Calcul de l'Indice d'Attractivité dynamique
    df_base['Indice_Attractivite'] = (df_base['Flux_Pietons_Journalier'] * coef_pietons) + (df_base['Custo_Luvas_Total_R$'] * 0.0001 * coef_visibilité)
    
    # Tri par indice d'attractivité décroissant
    df_base = df_base.sort_values(by='Indice_Attractivite', ascending=False).reset_index(drop=True)
    df_base.index = df_base.index + 1  # Pour que le classement commence à 1 au lieu de 0
    
    df_faisable = df_base[df_base['Faisable'] == True]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🏆 Top 5 des Rues Recommandées (Dans ton budget)")
        if not df_faisable.empty:
            # Affichage propre avec les colonnes demandées (Classement implicite via l'index 1, 2, 3...)
            cols_to_show = ['Bairro', 'Rua', 'Luvas_Total_Surface', 'Aluguel_Mensal_R$', 'Indice_Attractivite']
            st.dataframe(df_faisable[cols_to_show].head(5), use_container_width=True)
        else:
            st.warning("⚠️ Aucun bien ne rentre dans ton enveloppe de Luvas actuelle avec cette surface.")
            
    with col2:
        st.subheader("📊 Synthèse du Projet")
        st.metric("Rues éligibles", f"{len(df_faisable)} / {len(df_base)}")
        st.metric("Surface testée", f"{surface_cible} m²")

    st.subheader("🗺️ Carte Interactive des Opportunités (Zona Sul)")
    view_state = pdk.ViewState(latitude=-22.9711, longitude=-43.1822, zoom=12, pitch=30)
    
    # Vert si faisable dans le budget, Rouge si hors budget
    df_base['color'] = df_base['Faisable'].apply(lambda x: [0, 200, 100, 180] if x else [200, 50, 50, 140])

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_base,
        get_position=["Longitude", "Latitude"],
        get_color="color",
        get_radius=250,
        pickable=True,
        auto_highlight=True,
    )

    r = pdk.Deck(
        layers=[layer], 
        initial_view_state=view_state, 
        tooltip={
            "text": "Quartier: {Bairro}\nRue: {Rua}\nLuvas Total: {Luvas_Total_Surface:,.0f} R$\nLoyer Mensuel: {Aluguel_Mensal_R$:,.0f} R$\nIndice Attractivité: {Indice_Attractivite:.1f}\nFaisable: {Faisable}"
        }
    )
    st.pydeck_chart(r)
