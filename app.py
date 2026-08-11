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

st.title("Simulador de Seleção de Ponto Comercial - Zona Sul")

@st.cache_data
def load_data():
    try:
        df_main = pd.read_csv("database_rio.csv")
        df_main.columns = df_main.columns.str.strip()
        df_main['Rua'] = df_main['Rua'].astype(str).str.strip()
        df_main['Bairro'] = df_main['Bairro'].astype(str).str.strip()
        
        df_geo = pd.read_csv("Base_Data_Geo_rio.csv")
        df_geo.columns = df_geo.columns.str.strip()
        df_geo['Rua'] = df_geo['Rua'].astype(str).str.strip()
        df_geo['Bairro'] = df_geo['Bairro'].astype(str).str.strip()
        
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

        df = pd.merge(df_main, df_geo[['Rua', 'Bairro', 'path']], on=['Rua', 'Bairro'], how='left')
        
        default_path = [[-43.1905, -22.9645], [-43.1780, -22.9750]]
        df['path'] = df['path'].apply(lambda x: x if isinstance(x, list) and len(x) > 0 else default_path)
        
        return df
    except Exception as e:
        st.error(f"Erreur de chargement des fichiers : {e}")
        return pd.DataFrame()

df_base = load_data()

if not df_base.empty:
    st.sidebar.header("Centros de custos (R$)")
    c_travaux = st.sidebar.number_input("Custo Obras Fixo (R$)", value=170000, step=5000, key="c_travaux")
    c_equip = st.sidebar.number_input("Custo Equipamentos (R$)", value=190763, step=5000, key="c_equip")
    c_mobilier = st.sidebar.number_input("Custo Mobiliário (R$)", value=20832, step=1000, key="c_mobilier")
    c_marketing = st.sidebar.number_input("Custo Marketing (R$)", value=18500, step=1000, key="c_marketing")
    c_admin = st.sidebar.number_input("Custo Administrativo (R$)", value=18000, step=1000, key="c_admin")
    c_secu = st.sidebar.number_input("Custo Segurança (R$)", value=17000, step=1000, key="c_secu")
    c_ti = st.sidebar.number_input("Custo TI (R$)", value=5000, step=500, key="c_ti")
    c_reserves = st.sidebar.number_input("Reserva de Emergência (R$)", value=93000, step=5000, key="c_reserves")

    total_fixes = c_travaux + c_equip + c_mobilier + c_marketing + c_admin + c_secu + c_ti + c_reserves

    st.markdown("---")
    
    # Disposition avec une colonne vide au milieu pour créer un espace propre
    col_desc, col_space, col_sliders = st.columns([1.5, 0.3, 2])
    
    with col_desc:
        st.markdown(
            "O \"Simulador de Seleção de Ponto Comercial\" é uma ferramenta desenvolvida para identificar "
            "a escolha de locais para novos restaurantes na Zona Sul do Rio de Janeiro. "
            "A plataforma cruza dados financeiros personalizados (o aporte disponível, os centros de custos, etc) "
            "com métricas de mercado fundamentais, incluindo o índice de fluxo de pedestres, a atratividade da rua "
            "e os custos de aluguel e luvas. Ao ajustar variáveis de investimento e metragem, o usuário visualiza "
            "instantaneamente a viabilidade econômica de cada endereço. O sistema ranqueia automaticamente as 10 melhores "
            "ruas para o negócio e projeta esses dados em um mapa interativo, permitindo uma tomada de decisão precisa e rapida, "
            "baseada em dados reais e adaptada ao orçamento de cada empreendedor."
        )
        
    with col_sliders:
        sub_col1, sub_col2 = st.columns([1.3, 0.7])
        with sub_col1:
            orçamento_luvas_disponivel = st.slider("Enveloppe Luvas Disponible (R$)", min_value=50000, max_value=500000, value=200000, step=10000, key="slider_luvas")
            surface_cible = st.slider("Surface Cible (m²)", min_value=30, max_value=120, value=55, step=5, key="slider_surface")
        with sub_col2:
            user_apport = total_fixes + orçamento_luvas_disponivel
            st.metric(label="Apport Total Calculé (R$)", value=f"{user_apport:,.0f} R$")
        
    st.markdown("---")

# Calculs financiers par rue
df_base['Luvas_Total'] = df_base['Custo_Luvas_m2_R$'] * surface_cible
df_base['Aluguel_Mensal_Total'] = df_base['Aluguel_Mensal_m2_R$'] * surface_cible
df_base['Investimento_Total'] = df_base['Luvas_Total'] + total_fixes

# Formatage BR pour les tooltips
def br_currency(x):
    return f"{x:,.0f}".replace(",", ".")

df_base["Luvas_FMT"] = df_base["Luvas_Total"].apply(br_currency)
df_base["Aluguel_FMT"] = df_base["Aluguel_Mensal_Total"].apply(br_currency)
df_base["Score_FMT"] = df_base["Score_Global_Final"].round(1)

# Test de faisabilité
df_base['Faisable'] = df_base['Luvas_Total'] <= orçamento_luvas_disponivel

    # Filtrage et Tri par Score Global décroissant (Attractivité de la rue)
    df_faisable = df_base[df_base['Faisable'] == True].copy()
    df_faisable = df_faisable.sort_values(by=['Score_Global_Final', 'Indice_Fluxo_Pedestres'], ascending=False).reset_index(drop=True)
    df_faisable.index = df_faisable.index + 1

    st.subheader("Ranking das 10 Melhores Ruas para Implantação")
    if not df_faisable.empty:
        df_display = df_faisable.head(10).copy()
        df_display = df_display.rename(columns={
            'Bairro': 'Bairro',
            'Rua': 'Rua',
            'Indice_Fluxo_Pedestres': 'Fluxo de pedestres',
            'Score_Global_Final': 'Atratividade da rua',
            'Aluguel_Mensal_Total': 'Aluguel mensal (R$)',
            'Luvas_Total': 'Luvas (R$)',
            'Investimento_Total': 'Investimento total (R$)'
        })
        
        cols_to_show = [
            'Bairro', 'Rua', 'Fluxo de pedestres', 
            'Atratividade da rua', 'Aluguel mensal (R$)', 
            'Luvas (R$)', 'Investimento total (R$)'
        ]
        
        st.dataframe(df_display[cols_to_show].style.format({
            'Fluxo de pedestres': '{:,.0f}',
            'Atratividade da rua': '{:.1f}',
            'Aluguel mensal (R$)': '{:,.0f} R$',
            'Luvas (R$)': '{:,.0f} R$',
            'Investimento total (R$)': '{:,.0f} R$'
        }), use_container_width=True)
    else:
        st.warning("⚠️ Aucune rue ne respecte ton budget actuel avec cette surface.")

# ==========================================
# CARTE INTERACTIVE
# ==========================================

st.subheader("Mapeamento das Ruas")

score_min = float(df_base["Score_Global_Final"].min())
score_max = float(df_base["Score_Global_Final"].max())

def interpolate(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
        220
    ]

def get_color(row):
    if not row["Faisable"]:
        return [110, 110, 110, 180]

    score = float(row["Score_Global_Final"])
    ratio = (score - score_min) / (score_max - score_min) if score_max != score_min else 0.5

    red_color = [240, 150, 150]
    yellow_color = [255, 217, 0]
    green_color = [0, 176, 80]

    if ratio <= 0.5:
        t = ratio * 2
        return interpolate(red_color, yellow_color, t)
    else:
        t = (ratio - 0.5) * 2
        return interpolate(yellow_color, green_color, t)

df_base["color"] = df_base.apply(get_color, axis=1)

view_state = pdk.ViewState(
    latitude=-22.9711,
    longitude=-43.1822,
    zoom=12.8,
    pitch=0
)

layer = pdk.Layer(
    "PathLayer",
    data=df_base,
    get_path="path",
    get_color="color",
    width_scale=40,
    width_min_pixels=6,
    rounded=True,
    pickable=True,
    auto_highlight=True
)

r = pdk.Deck(
    map_style=pdk.map_styles.CARTO_LIGHT,
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": """
        <div style="
            background-color:white;
            padding:10px;
            border-radius:8px;
            font-size:14px;
        ">
            <b>{Rua}</b><br><br>
            <b>Quartier :</b> {Bairro}<br>
            <b>Flux Piétons :</b> {Indice_Fluxo_Pedestres}<br>
            <b>Score Global :</b> {Score_Global_Final}<br>
            <b>Luvas :</b> R$ {Luvas_Total:,.0f}<br>
            <b>Loyer :</b> R$ {Aluguel_Mensal_Total:,.0f}
        </div>
        """
    }
)

st.pydeck_chart(r)
