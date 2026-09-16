import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Eagles Praha - Analytika", layout="wide")

st.title("🦅 Eagles Praha - Pálkařská Analytika")
st.markdown("Interaktivní dashboard ze všech stažených play-by-play dat sezóny 2026.")

# 1. NAČTENÍ DAT (cache zajistí bleskové načítání)
@st.cache_data
def load_data():
    df = pd.read_csv('eagles_data_web.csv')
    df['text_lower'] = df['Popis_Akce'].fillna('').str.lower()
    
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

# Zde jsou všichni "falešní" pálkaři a soupeři, které nechceme vidět
blacklist = [
    "David KřEčEK",
    "Eduard NOSEK", "Jakub HAJTMAR", "Kamil PEJCHAL", "Marian HARIG",
    "Michal POKORNý", "Michal ZELENKA", "Milan PROKOP", "Neznámý",
    "Ondřej HRDLIčKA", "Tomáš BOHáč"
]

# Vyfiltrujeme čistý roster Eagles (vyhodíme blacklist)
hraci_eagles = sorted([h for h in df['Pálkař'].unique() if h not in blacklist])

# Do roletky přidáme na první místo možnost "Celý tým"
moznosti_vyberu = ["Celý tým"] + hraci_eagles

vybrany_hrac = st.sidebar.selectbox("Vyber pálkaře:", moznosti_vyberu)
faze_sezony = st.sidebar.radio("Fáze sezóny:", ["Vše", "Základní část", "Playoff"])

# Aplikace filtrů na DataFrame
if vybrany_hrac == "Celý tým":
    # Pokud chce celá čísla, omezíme data jen na validní roster Eagles (bez soupeřů)
    df_filt = df[df['Pálkař'].isin(hraci_eagles)]
else:
    # Pokud vybral jednoho hráče
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
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Švihání na 1. nadhoz (Stav 0-0)")
        df_0_0 = df_filt[df_filt['Count'] == '0-0'].copy()
        df_0_0['Swing'] = df_0_0['text_lower'].str.contains('swinging strike|foul').astype(int) | df_0_0['AB_flag'] | df_0_0['SF'] | df_0_0['SH']
        
        celkem_0_0 = len(df_0_0)
        svihy = df_0_0['Swing'].sum()
        pct = (svihy / celkem_0_0 * 100) if celkem_0_0 > 0 else 0
        
        st.metric("Agresivita na první nadhoz", f"{pct:.1f} %", f"{svihy} švihů z {celkem_0_0} nadhozů", delta_color="off")
        
        st.subheader("Z jakého stavu dáváme Hity?")
        df_hits = df_filt[df_filt['H'] == 1]
        hit_counts = df_hits['Count'].value_counts().reset_index()
        hit_counts.columns = ['Stav (Count)', 'Počet Hitů']
        st.dataframe(hit_counts, hide_index=True)

    with col2:
        st.subheader("Úspěšnost (AVG) podle stavu")
        df_ab = df_filt[df_filt['AB_flag'] == 1]
        count_stats = df_ab.groupby('Count').agg(
            AB=('AB_flag', 'sum'),
            Hity=('H', 'sum')
        ).reset_index()
        count_stats['AVG'] = (count_stats['Hity'] / count_stats['AB']).round(3)
        count_stats = count_stats.sort_values(by='AVG', ascending=False)
        st.dataframe(count_stats, hide_index=True)

with tab2:
    st.write("Kompletní historie nadhozů pro tento výběr:")
    zobrazene_sloupce = ['Zápas_ID', 'Fáze', 'Směna', 'Outy', 'Count', 'Pálkař', 'Nadhazovač', 'Popis_Akce']
    st.dataframe(df_filt[zobrazene_sloupce], use_container_width=True, hide_index=True)