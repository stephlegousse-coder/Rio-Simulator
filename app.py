import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(
    page_title="Rio Location Simulator",
    page_icon="🇧🇷",
    layout="wide"
)

st.title("🇧🇷 Simulateur Stratégique & Foncier - Zona Sul (Rio)")
st.markdown("Analyse des rues de la Zona Sul avec scoring piéton et cartographie interactive.")

# -------------------------------------------------------------
# 1. CHARGEMENT DE LA BASE DE DONNÉES DEPUIS LE CSV SUR GITHUB
# -------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("database_rio.csv")
        return df
    except Exception as e:
        st.error(f"Erreur : Impossible de trouver le fichier 'database_rio.csv' sur GitHub. Détails : {e}")
        return pd.DataFrame()

df_base = load_data()

if not df_base.empty:
    # Affiche les colonnes détectées pour t'aider à vérifier si besoin
    # st.write("Colonnes trouvées dans ton CSV :", list(df_base.columns))
    
    # -------------------------------------------------------------
    # 2. PANNEAU LATÉRAL (Paramètres & Poids)
    # -------------------------------------------------------------
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

    st.sidebar.markdown("---")
    st.sidebar.header("⚖️ Poids des Variables (Score Global)")
    p_pietons = st.sidebar.slider("Poids Flux Piétons (Prioritaire)", 0.0, 5.0, 2.0, 0.1)
    p_comercios = st.sidebar.slider("Poids Comércios Existentes", 0.0, 5.0, 1.0, 0.1)
    p_renda = st.sidebar.slider("Poids Renda Média", 0.0, 5.0, 1.2, 0.1)
    p_concurrence = st.sidebar.slider("Poids Concentration Concurrence", 0.0, 5.0, 1.0, 0.1)
    p_delivery = st.sidebar.slider("Poids Potentiel Delivery", 0.0, 5.0, 1.3, 0.1)

    # -------------------------------------------------------------
    # 3. VERIFICATION ET ADAPTATION DES NOMS DE COLONNES
    # -------------------------------------------------------------
    # Nettoyage des espaces potentiels dans les noms de colonnes du CSV
    df_base.columns = df_base.columns.str.strip()

    # Détection automatique de la colonne Luvas si le nom exact diffère
    col_luvas = None
    for c in ['Custo_Luvas_Total_R$', 'Custo_Luvas_Total', 'Luvas', 'Custo_Luvas']:
        if c in df_base.columns:
            col_luvas = c
            break
            
    col_pietons = None
    for c in ['Indice_Fluxo_Pedestres', 'Flux_Pietons', 'Pedestres']:
        if c in df_base.columns:
            col_pietons = c
            break

    if not col_luvas or not col_pietons:
        st.error(f"⚠️ Colonnes introuvables dans ton CSV. Voici les colonnes présentes dans ton fichier : {list(df_base.columns)}")
    else:
        # -------------------------------------------------------------
        # 4. CALCULS & FILTRAGE
        # -------------------------------------------------------------
        def normalize(series):
            return (series - series.min()) / (series.max() - series.min() + 1e-5) * 100

        df_base['Norm_Pietons'] = normalize(df_base[col_pietons])
        df_base['Norm_Comercios'] = normalize(df_base['Qtd_Comércios_existentes']) if 'Qtd_Comércios_existentes' in df_base.columns else 0
        df_base['Norm_Renda'] = normalize(df_base['Renda_média_Familiar_R$']) if 'Renda_média_Familiar_R$' in df_base.columns else 0
        df_base['Norm_Conc'] = normalize(df_base['Coef_Concentration_Conc']) if 'Coef_Concentration_Conc' in df_base.columns else 0
        df_base['Norm_Delivery'] = normalize(df_base['Potencial_Delivery_Score']) if 'Potencial_Delivery_Score' in df_base.columns else 0

        somme_poids = p_pietons + p_comercios + p_renda + p_concurrence + p_delivery
        df_base['Score_Global_Final'] = (
            (df_base['Norm_Pietons'] * p_pietons) +
            (df_base['Norm_Comercios'] * p_comercios) +
            (df_base['Norm_Renda'] * p_renda) +
            (df_base['Norm_Conc'] * p_concurrence) +
            (df_base['Norm_Delivery'] * p_delivery)
        ) / somme_poids

        # Application de la surface sur le luvas total
        df_base['Luvas_Total_Surface'] = df_base[col_luvas] * (surface_cible / 55)

        # Faisabilité budgétaire
        df_base['Faisable'] = df_base['Luvas_Total_Surface'] <= orçamento_luvas_disponivel

        # Filtrage : On ne garde que les rues faisables
        df_faisable = df_base[df_base['Faisable'] == True].copy()

        # Tri par Flux Piétons d'abord, puis Score Global
        df_faisable = df_faisable.sort_values(by=[col_pietons, 'Score_Global_Final'], ascending=False).reset_index(drop=True)
        df_faisable.index = df_faisable.index + 1  # Classement de 1 à 10

        # -------------------------------------------------------------
        # 5. AFFICHAGE INTERFACE (Top 10)
        # -------------------------------------------------------------
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🏆 Top 10 des Rues (Faisables & Triées par Flux Piéton)")
            if not df_faisable.empty:
                cols_to_show = ['Bairro', 'Rua', col_pietons, 'Luvas_Total_Surface', 'Aluguel_Mensal_R$', 'Score_Global_Final']
                st.dataframe(df_faisable[cols_to_show].head(10).style.format({
                    col_pietons: '{:,.0f}',
                    'Luvas_Total_Surface': '{:,.0f} R$',
                    'Aluguel_Mensal_R$': '{:,.0f} R$',
                    'Score_Global_Final': '{:.1f} / 100'
                }), use_container_width=True)
            else:
                st.warning("⚠️ Aucune rue ne respecte ton budget actuel avec cette surface.")

        with col2:
            st.subheader("📊 Synthèse Globale")
            st.metric("Rues éligibles au budget", f"{len(df_faisable)} / {len(df_base)}")
            st.metric("Surface testée", f"{surface_cible} m²")

        # -------------------------------------------------------------
        # 6. CARTE INTERACTIVE
        # -------------------------------------------------------------
        st.subheader("🗺️ Cartographie des 540 Rues (Zona Sul)")

        def get_color(row):
            if not row['Faisable']:
                return [200, 50, 50, 80]  
            score = row['Score_Global_Final']
            if score > 75:
                return [0, 220, 100, 200]  
            elif score > 50:
                return [50, 150, 250, 200] 
            elif score > 25:
                return [250, 200, 0, 200]  
            else:
                return [200, 100, 50, 200] 

        df_base['color'] = df_base.apply(get_color, axis=1)

        view_state = pdk.ViewState(latitude=-22.9711, longitude=-43.1822, zoom=12, pitch=30)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_base,
            get_position=["Longitude", "Latitude"],
            get_color="color",
            get_radius=120,
            pickable=True,
            auto_highlight=True,
        )

        r = pdk.Deck(
            layers=[layer], 
            initial_view_state=view_state, 
            tooltip={
                "text": "Quartier: {Bairro}\nRue: {Rua}\nFlux Piétons: {" + col_pietons + "}\nScore Global: {Score_Global_Final:.1f}\nLuvas Total: {Luvas_Total_Surface:,.0f} R$\nLoyer: {Aluguel_Mensal_R$:,.0f} R$\nFaisable: {Faisable}"
            }
        )
        st.pydeck_chart(r)
