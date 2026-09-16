import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Eagles Praha - Analytika", layout="wide")

st.title("Eagles Praha - Pálkařská Analytika")
st.markdown("Interaktivní dashboard ze všech stažených play-by-play dat sezóny 2026. Pokud nevidíte nastavení - rozklikněte vlevo nahoře >> (výběr hráče/části)")

# 1. NAČTENÍ A FILTRACE DAT (cache zajistí bleskové načítání)
@st.cache_data
def load_data():
    df = pd.read_csv('eagles_data_web.csv') # Název tvého souboru na GitHubu
    df['text_lower'] = df['Popis_Akce'].fillna('').str.lower()
    
    # =========================================================
    # 🚨 ULTIMÁTNÍ FILTR: LOKACE NADHOZU + VALIDNÍ AKCE 🚨
    # =========================================================
    ma_lokaci = df['Pitch_Y'] > 0

    ma_akci = (
        (df['Je_Hit'] == 1) | 
        (df['Je_Walk'] == 1) | 
        (df['Outy'] > 0) | 
        df['text_lower'].str.contains('strikes out|grounds out|flies out|lines out|pops out|error|wild pitch|passed ball')
    )

    nesmysly = df['text_lower'].str.contains('end of the|middle of the|coaching visit|defensive conference|play ball')

    df = df[(ma_lokaci | ma_akci) & (~nesmysly)].copy()
    # =========================================================

    # Výpočetní sloupce pro analýzu AB
    df['H'] = df['text_lower'].str.contains('singles|doubles|triples|homers').astype(int)
    df['SO'] = df['text_lower'].str.contains('strikes out|strikeout error').astype(int)
    df['Out_In_Play'] = df['text_lower'].str.contains('grounds out|flies out|pops out|lines out|reaches on|hits into').astype(int)
    df['SF'] = df['text_lower'].str.contains('sacrifice fly').astype(int)
    df['SH'] = df['text_lower'].str.contains('sacrifice bunt|sac bunt|sacrifice hit').astype(int)
    
    df['AB_flag'] = df['H'] + df['SO'] + df['Out_In_Play']
    df.loc[(df['SF'] == 1) | (df['SH'] == 1), 'AB_flag'] = 0
    df['Count'] = df['Stav_Balls'].astype(str) + "-" + df['Stav_Strikes'].astype(str)
    
    return df

df = load_data()

# =========================================================
# 2. FILTROVÁNÍ HRÁČŮ (BLACKLIST)
# =========================================================
st.sidebar.header("Nastavení")

# Blacklist soupeřů a chyb zápisu
blacklist = [
    "Caleb FREEMAN", "Adam TOšOVSKý", "Filip NěMEC", "David KřEčEK",
    "Eduard NOSEK", "Jakub HAJTMAR", "Kamil PEJCHAL", "Marian HARIG",
    "Michal POKORNý", "Michal ZELENKA", "Milan PROKOP", "Neznámý",
    "Ondřej HRDLIčKA", "Tomáš BOHáč"
]

hraci_eagles = sorted([h for h in df['Pálkař'].unique() if h not in blacklist])

moznosti_vyberu = ["Celý tým"] + hraci_eagles

vybrany_hrac = st.sidebar.selectbox("Vyber pálkaře:", moznosti_vyberu)
faze_sezony = st.sidebar.radio("Fáze sezóny:", ["Vše", "Základní část", "Playoff"])

# Aplikace filtrů na DataFrame
if vybrany_hrac == "Celý tým":
    df_filt = df[df['Pálkař'].isin(hraci_eagles)]
else:
    df_filt = df[df['Pálkař'] == vybrany_hrac]

if faze_sezony != "Vše":
    df_filt = df_filt[df_filt['Fáze'] == faze_sezony]

# =========================================================
# 3. ZOBRAZENÍ VÝSLEDKŮ
# =========================================================
st.header(f"📊 {vybrany_hrac}")
st.write(f"Zobrazeno nadhozů/akcí: **{len(df_filt)}**")

tab1, tab2 = st.tabs(["Situační Analýza", "Surová data"])

with tab1:
    # Rozdělíme obrazovku na 3 sloupce místo 2, ať se tam vejde i analýza Strikeoutů
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Švihání na 1. nadhoz (Stav 0-0)")
        df_0_0 = df_filt[df_filt['Count'] == '0-0'].copy()
        
        # Identifikace švihů a ballů
        df_0_0['Swing'] = df_0_0['text_lower'].str.contains('swinging strike|foul').astype(int) | df_0_0['AB_flag'] | df_0_0['SF'] | df_0_0['SH']
        df_0_0['is_ball'] = df_0_0['text_lower'].str.startswith('ball') | df_0_0['text_lower'].str.contains('walks')
        
        svihy_0_0 = df_0_0['Swing'].sum()
        celkem_0_0 = len(df_0_0)
        bally_0_0 = df_0_0['is_ball'].sum()
        
        # Tvůj vzorec: (všechny nadhozy - ty co byly ball)
        mozne_svihy_0_0 = celkem_0_0 - bally_0_0 
        pct_0_0 = (svihy_0_0 / mozne_svihy_0_0 * 100) if mozne_svihy_0_0 > 0 else 0
        
        st.metric("Agresivita na první nadhoz", f"{pct_0_0:.1f} %", f"{svihy_0_0} švihů z {mozne_svihy_0_0} hratelných míčů", delta_color="off")
        
        # ---------------------------------------------------------
        # NOVÉ: ŠVIHÁNÍ NA PRVNÍ STRIKE (Stavy 0-0, 1-0, 2-0, 3-0)
        # ---------------------------------------------------------
        st.subheader("Švihání na 1. strike (Stav 0 striků)")
        
        # Vybereme všechny stavy, kdy je stav striků přesně 0
        df_0_strike = df_filt[df_filt['Stav_Strikes'].astype(str) == '0'].copy()
        
        df_0_strike['Swing'] = df_0_strike['text_lower'].str.contains('swinging strike|foul').astype(int) | df_0_strike['AB_flag'] | df_0_strike['SF'] | df_0_strike['SH']
        df_0_strike['is_ball'] = df_0_strike['text_lower'].str.startswith('ball') | df_0_strike['text_lower'].str.contains('walks')
        
        svihy_0_strike = df_0_strike['Swing'].sum()
        celkem_0_strike = len(df_0_strike)
        bally_0_strike = df_0_strike['is_ball'].sum()
        
        mozne_svihy_0_strike = celkem_0_strike - bally_0_strike
        pct_0_strike = (svihy_0_strike / mozne_svihy_0_strike * 100) if mozne_svihy_0_strike > 0 else 0
        
        st.metric("Agresivita bez striku", f"{pct_0_strike:.1f} %", f"{svihy_0_strike} švihů z {mozne_svihy_0_strike} hratelných míčů", delta_color="off")
        
        st.divider() # Vizuální oddělovací čára
        
        if vybrany_hrac == "Celý tým":
             # Zobrazení tabulky pro celý tým na první strike (0 striků)
             first_strike_stats = df_0_strike.groupby('Pálkař').agg(
                 Total_Pitches=('Count', 'count'),
                 Balls=('is_ball', 'sum'),
                 Swings=('Swing', 'sum')
             ).reset_index()
             
             first_strike_stats['Hratelne'] = first_strike_stats['Total_Pitches'] - first_strike_stats['Balls']
             # Zabráníme dělení nulou
             first_strike_stats = first_strike_stats[first_strike_stats['Hratelne'] > 0]
             first_strike_stats['Swing_%'] = (first_strike_stats['Swings'] / first_strike_stats['Hratelne'] * 100).round(1)
             
             first_strike_stats = first_strike_stats[first_strike_stats['Total_Pitches'] >= 3]
             first_strike_stats = first_strike_stats.sort_values(by='Swing_%', ascending=False)
             
             st.write("Kdo nejvíc švihá hratelné míče (Stav 0 striků):")
             # Ukážeme jen to nejdůležitější, ať se to vejde
             st.dataframe(first_strike_stats[['Pálkař', 'Swings', 'Hratelne', 'Swing_%']], hide_index=True, use_container_width=True)
        else:
             st.subheader("Z jakého stavu dává Hity?")
             df_hits = df_filt[df_filt['H'] == 1]
             hit_counts = df_hits['Count'].value_counts().reset_index()
             hit_counts.columns = ['Stav (Count)', 'Počet Hitů']
             st.dataframe(hit_counts, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("Typy Strikeoutů (SO)")
        # ⚾ ZDE JE NOVÁ ANALÝZA STRIKEOUTŮ ⚾
        df_so = df_filt[df_filt['SO'] == 1].copy()
        
        so_swinging = df_so['text_lower'].str.contains('swinging').sum()
        so_looking = df_so['text_lower'].str.contains('looking').sum()
        so_celkem = so_swinging + so_looking
        
        if so_celkem > 0:
            pct_swinging = (so_swinging / so_celkem * 100)
            pct_looking = (so_looking / so_celkem * 100)
            
            st.metric("Celkem SO", so_celkem)
            
            # Vykreslení jednoduchého koláčového grafu přímo ve Streamlitu
            import plotly.express as px # Pokud používáš plotly (pip install plotly)
            # Pokud ne, můžeme udělat jen textový výpis:
            
            st.write(f"**Swinging:** {so_swinging} ({pct_swinging:.1f}%)")
            st.write(f"**Looking:** {so_looking} ({pct_looking:.1f}%)")
            
            # Progress bar pro vizualizaci poměru
            st.progress(int(pct_swinging), text="Poměr švihnutých (vs puštěných) strikeoutů")
        else:
            st.write("Zatím žádné strikeouty! 🎉")

    with col3:
        st.subheader("Úspěšnost (AVG) podle stavu")
        df_ab = df_filt[df_filt['AB_flag'] == 1]
        count_stats = df_ab.groupby('Count').agg(
            AB=('AB_flag', 'sum'),
            Hity=('H', 'sum')
        ).reset_index()
        count_stats['AVG'] = (count_stats['Hity'] / count_stats['AB']).round(3)
        min_ab = 2 if vybrany_hrac != "Celý tým" else 5 
        count_stats = count_stats[count_stats['AB'] >= min_ab]
        count_stats = count_stats.sort_values(by='AVG', ascending=False)
        st.dataframe(count_stats, hide_index=True)
        
        if vybrany_hrac == "Celý tým":
            st.subheader("Z jakého stavu dává tým Hity?")
            df_hits = df_filt[df_filt['H'] == 1]
            hit_counts = df_hits['Count'].value_counts().reset_index()
            hit_counts.columns = ['Stav (Count)', 'Počet Hitů']
            st.dataframe(hit_counts, hide_index=True)

with tab2:
    st.write("Kompletní historie nadhozů pro tento výběr:")
    zobrazene_sloupce = ['Zápas_ID', 'Fáze', 'Směna', 'Outy', 'Count', 'Pálkař', 'Nadhazovač', 'Popis_Akce']
    st.dataframe(df_filt[zobrazene_sloupce], use_container_width=True, hide_index=True)