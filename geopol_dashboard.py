import streamlit as st
import yfinance as yf
import feedparser
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from time import mktime
from datetime import datetime
import map_module 

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(layout="wide", page_title="STRATEGIC TERMINAL v10.7", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0b0c10; color: #f4f4f5; }
    .block-container { padding-top: 1rem !important; max-width: 98%; }
    
    [data-testid="stSidebar"] { background-color: #121214 !important; border-right: 1px solid #27272a; }
    [data-testid="stSidebar"] .css-17lntkn { color: #f4f4f5; font-weight: 700; letter-spacing: 1px;}
    div[data-baseweb="select"] > div { background-color: #0b0c10; border: 1px solid #27272a; color: #4ade80; font-weight: bold; }
    div[data-baseweb="select"] > div:hover { border-color: #4ade80; }
    div[data-baseweb="checkbox"] { margin-bottom: 5px; }
    
    .wm-header { color: #f4f4f5; font-size: 1rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; border-bottom: 1px solid #27272a; padding-bottom: 10px; }
    
    .wm-card { background-color: #14151a; border: 1px solid #23252d; border-radius: 4px; padding: 10px; height: 185px; margin-bottom: 10px; display: flex; flex-direction: column; }
    .tg-card { background-color: #1a1e24; border: 1px solid #3b82f6; border-left: 4px solid #3b82f6; border-radius: 4px; padding: 10px; height: 160px; margin-bottom: 10px; display: flex; flex-direction: column; overflow: hidden; }
    .x-card { background-color: #121214; border: 1px solid #3f3f46; border-left: 4px solid #f4f4f5; border-radius: 4px; padding: 10px; height: 160px; margin-bottom: 10px; display: flex; flex-direction: column; overflow: hidden; }
    
    .tg-author { color: #60a5fa; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;}
    .x-author { color: #f4f4f5; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;}
    .tg-text { color: #e2e8f0; font-size: 0.8rem; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; margin-bottom: auto;}
    
    .card-hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .card-lbl { color: #64748b; font-size: 0.6rem; font-weight: 800; text-transform: uppercase; }
    
    .live-badge { color: #4ade80; font-size: 0.55rem; padding: 2px 6px; border: 1px solid #4ade80; font-weight: 700; border-radius: 2px; background-color: rgba(74,222,128,0.05); }
    .tg-badge { color: #3b82f6; font-size: 0.55rem; padding: 2px 6px; border: 1px solid #3b82f6; font-weight: 700; border-radius: 2px; background-color: rgba(59,130,246,0.05); }
    .x-badge { color: #f4f4f5; font-size: 0.55rem; padding: 2px 6px; border: 1px solid #f4f4f5; font-weight: 700; border-radius: 2px; background-color: rgba(244,244,245,0.05); }
    
    .news-meta { display: flex; justify-content: space-between; font-size: 0.65rem; font-weight: 700; margin-bottom: 4px; }
    .news-src { color: #fbbf24; text-transform: uppercase; }
    .news-time { color: #94a3b8; font-weight: 400; font-size: 0.65rem; }
    .news-title { color: #e2e8f0; font-size: 0.85rem; font-weight: 600; line-height: 1.3; margin-bottom: 5px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
    .news-smry { color: #94a3b8; font-size: 0.75rem; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    
    .eco-widget { background: #121214; border: 1px solid #27272a; border-radius: 4px; padding: 8px; height: 70px; display: flex; flex-direction: column; justify-content: center;}
    .eco-label { color: #a1a1aa; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; margin-bottom: 2px;}
    .eco-value { color: #f4f4f5; font-size: 1.1rem; font-weight: 700; }
    .eco-sym { color: #4ade80; font-size: 0.8rem; margin-right: 2px; }
    
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] { scrollbar-width: thin; scrollbar-color: #4ade80 #14151a; }
    </style>
    """, unsafe_allow_html=True)

SCENARIOS = {
    "Analisi Globale": {"rss": "geopolitics+security", "kws": ["geopolitics", "military", "war"], "tg": ["geopolitics_live", "disclosetv"], "x": ["OSINTdefender", "clashreport"]},
    "Medio Oriente": {"rss": "middle+east+israel+iran", "kws": ["israel", "iran", "gaza"], "tg": ["Middle_East_Spectator", "FarsNewsInt", "me_observer_TG"], "x": ["Faytuks", "AuroraIntel"]},
    "Europa / NATO": {"rss": "ukraine+russia+nato", "kws": ["ukraine", "russia", "nato"], "tg": ["liveukraine_media", "DDGeopolitics"], "x": ["Tendar", "NOELreports"]},
    "Asia-Pacifico": {"rss": "taiwan+china+military", "kws": ["taiwan", "china", "korea"], "tg": ["CCTV_english"], "x": ["IndoPac_Info"]},
    "Americhe": {"rss": "usa+election+security", "kws": ["usa", "election", "cartel"], "tg": ["disclosetv"], "x": ["visegrad24"]},
    "Africa": {"rss": "africa+conflict+war", "kws": ["africa", "sudan", "sahel"], "tg": ["africaintel"], "x": ["CasusBellii"]}
}

@st.cache_data(ttl=180)
def fetch_telegram_intel(channels):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'}
    for channel in channels:
        try:
            resp = requests.get(f"https://t.me/s/{channel}", headers=headers, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            dates = soup.find_all('time', class_='time')
            for msg, date in zip(messages[-15:], dates[-15:]):
                clean_text = msg.get_text(separator=" ", strip=True)
                if len(clean_text) > 20:
                    results.append({"channel": channel, "text": clean_text, "time": date.text, "link": f"https://t.me/{channel}", "platform": "TG"})
        except: continue
    return list(reversed(results))

@st.cache_data(ttl=300)
def fetch_x_intel(accounts):
    results = []
    bridges = ["https://nitter.poast.org", "https://nitter.privacydev.net"]
    for acc in accounts:
        success = False
        for bridge in bridges:
            if success: break
            try:
                feed = feedparser.parse(f"{bridge}/{acc}/rss")
                if feed.entries:
                    for item in feed.entries[:5]:
                        clean_text = BeautifulSoup(item.summary, 'html.parser').get_text(separator=" ", strip=True)
                        if len(clean_text) > 10:
                            results.append({"channel": acc, "text": clean_text, "time": "X Post", "link": item.link, "platform": "X"})
                    success = True
            except: pass
    return results

@st.cache_data(ttl=300)
def fetch_sorted_news(q):
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en").entries
    processed = []
    for item in feed:
        dt = datetime.fromtimestamp(mktime(item.published_parsed)) if hasattr(item, 'published_parsed') and item.published_parsed else datetime.now()
        item['dt'] = dt
        item['display_time'] = dt.strftime("%H:%M - %d/%m/%Y")
        processed.append(item)
    processed.sort(key=lambda x: x['dt'], reverse=True)
    return processed

@st.cache_data(ttl=600)
def get_manifold_predictions(keywords):
    try:
        resp = requests.get("https://api.manifold.markets/v0/search-markets", params={"filter": "open", "sort": "liquidity", "limit": 300}, timeout=10)
        results = []
        for m in resp.json():
            q = m.get('question', '').lower()
            prob = m.get('probability')
            if prob is not None and any(re.search(r'\b' + re.escape(k) + r'\b', q) for k in keywords):
                results.append({"t": m.get('question')[:90], "o": f"{prob*100:.0f}%"})
        return results[:8]
    except: return []

if 'page_news' not in st.session_state: st.session_state.page_news = 0
if 'page_socmint' not in st.session_state: st.session_state.page_socmint = 0
if 'page_adv' not in st.session_state: st.session_state.page_adv = 0

with st.sidebar:
    st.title("INTEL CONTROL")
    area = st.selectbox("Scenario Focus", list(SCENARIOS.keys()))
    st.divider()
    st.markdown("**LIVELLI MAPPA (SENSING)**")
    layer_thermal = st.checkbox("Sensori Termici (NASA)", value=True)
    layer_flights = st.checkbox("Tracciamento Voli (OpenSky)", value=False)
    layer_energy = st.checkbox("Infrastrutture Energetiche", value=True)
    layer_advisory = st.checkbox("Avvisi Sicurezza (USA & ITA)", value=True)
    
    if st.button("Forza Aggiornamento Mappa"):
        map_module.fetch_opensky_flights.clear()
        st.rerun()
        
    active_layers = []
    if layer_thermal: active_layers.append("Sensori Termici")
    if layer_flights: active_layers.append("Tracciamento Voli")
    if layer_energy: active_layers.append("Infrastrutture Energetiche")
    if layer_advisory: active_layers.append("Avvisi Sicurezza")

    st.divider()
    if st.button("Reset Terminal"): 
        st.session_state.page_news = 0
        st.session_state.page_socmint = 0
        st.session_state.page_adv = 0
        st.rerun()

# --- 0. MAPPA ---
st.markdown("<div class='wm-header'>SITUATIONAL AWARENESS MAP (24H SENSING)</div>", unsafe_allow_html=True)
map_module.render_strategic_map(area, active_layers)

# --- AVVISI DI SICUREZZA (Full Width) ---
if adv_list := map_module.fetch_security_advisories()[1]:
    with st.expander("REGISTRO AVVISI DI SICUREZZA (USA & ITA)", expanded=True):
        batch_adv = 4
        total_p_adv = max(1, (len(adv_list) - 1) // batch_adv + 1)
        current_adv = adv_list[st.session_state.page_adv * batch_adv : (st.session_state.page_adv + 1) * batch_adv]
        
        cols = st.columns(4)
        for j in range(4):
            if j < len(current_adv):
                item = current_adv[j]
                color = "#ef4444" if item['level'] == 4 else "#f97316" if item['level'] == 3 else "#fde047"
                with cols[j]:
                    st.markdown(f"""
                    <div style="background-color: #14151a; border: 1px solid {color}; border-left: 4px solid {color}; padding: 10px; border-radius: 4px; margin-bottom: 10px; height: 140px; display: flex; flex-direction: column;">
                        <div style="font-size: 0.65rem; font-weight: 800; color: {color}; margin-bottom: 3px;">{item['source']} | LVL {item['level']}</div>
                        <div style="color: #f4f4f5; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item['country']}</div>
                        <div style="color: #94a3b8; font-size: 0.75rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{item['title']}</div>
                        <a href="{item['link']}" target="_blank" style="color:#60a5fa; text-decoration:none; font-size:0.65rem; margin-top:auto;">Apri Fonte >></a>
                    </div>
                    """, unsafe_allow_html=True)
        
        a1, a2, a3 = st.columns([1, 2, 1])
        with a1:
            if st.button("<<", key="prev_adv") and st.session_state.page_adv > 0:
                st.session_state.page_adv -= 1
                st.rerun()
        with a2:
            st.markdown(f"<div style='text-align:center; font-size:0.65rem; color:#64748b; margin-top:10px;'>PAG. {st.session_state.page_adv + 1}/{total_p_adv}</div>", unsafe_allow_html=True)
        with a3:
            if st.button(">>", key="next_adv") and st.session_state.page_adv < total_p_adv - 1:
                st.session_state.page_adv += 1
                st.rerun()

# --- REGISTRO VOLI (Full Width) ---
if "Tracciamento Voli" in active_layers:
    df_flights = map_module.fetch_opensky_flights()
    if not df_flights.empty:
        with st.expander("REGISTRO VOLI ATTIVI SU MAPPA (Radar)", expanded=True):
            st.dataframe(
                df_flights[['callsign', 'icao', 'alt', 'vel', 'link']],
                column_config={"link": st.column_config.LinkColumn("Link Tracker", display_text="Traccia su ADSBExchange >>")},
                hide_index=True, use_container_width=True
            )

# --- INDICATORI ECONOMICI ---
st.write("")
m_cols = st.columns(6)
assets = [("BRENT OIL", "BZ=F", "$"), ("GOLD", "GC=F", "$"), ("USD/RUB", "RUB=X", "₽"), 
          ("USD/ILS", "ILS=X", "₪"), ("DOLLAR IDX", "DX-Y.NYB", "Pts"), ("BITCOIN", "BTC-USD", "$")]
for i, col in enumerate(m_cols):
    with col:
        name, tick, sym = assets[i]
        try:
            val = yf.Ticker(tick).fast_info['last_price']
            st.markdown(f'<div class="eco-widget"><div class="eco-label">{name}</div><div class="eco-value"><span class="eco-sym">{sym}</span>{val:.2f}</div></div>', unsafe_allow_html=True)
        except: st.markdown(f'<div class="eco-widget">{name}<br>N/A</div>', unsafe_allow_html=True)

# --- 1. GRIGLIA NEWS ---
st.markdown(f"<div class='wm-header' style='margin-top: 20px;'>TERMINALE OPERATIVO: {area.upper()}</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
area_config = SCENARIOS[area]

news = fetch_sorted_news(area_config["rss"])
forecasts = get_manifold_predictions(area_config["kws"])

batch_news = 9
total_p_news = max(1, (len(news) - 1) // batch_news + 1)
current_news = news[st.session_state.page_news * batch_news : (st.session_state.page_news + 1) * batch_news]

def draw_news(item):
    src = item.get('source', {}).get('title', 'INTEL SOURCE')
    smry = item.get('summary', '').split('<')[0][:100] + "..."
    return f"""
    <div class="wm-card">
        <div class="card-hdr"><span class="card-lbl">{area}</span><div class="live-badge">LIVE</div></div>
        <div class="news-meta"><span class="news-src">{src}</span><span class="news-time">{item['display_time']}</span></div>
        <div class="news-title">{item.title[:80]}...</div>
        <div class="news-smry">{smry}</div>
        <a href="{item.link}" target="_blank" style="color:#4ade80; text-decoration:none; font-size:0.65rem; margin-top:auto;">Apri Analisi >></a>
    </div>
    """

with c1:
    for item in current_news[0:3]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c2:
    for item in current_news[3:6]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c3:
    for item in current_news[6:9]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c4:
    st.markdown("<div class='card-lbl' style='margin-bottom:10px;'>Forecast Sentiment</div>", unsafe_allow_html=True)
    with st.container(height=580, border=False):
        if forecasts:
            for f in forecasts:
                with st.container(border=True):
                    st.markdown(f"<span style='color:#4ade80; font-weight:700; font-size:1.1rem;'>{f['o']}</span><br><span style='font-size:0.75rem; color:#d4d4d8;'>{f['t']}</span>", unsafe_allow_html=True)
        else: st.info("Nessuna previsione rilevata.")

n1, n2, n3 = st.columns([1, 2, 1])
with n1:
    if st.button("<< PREV NEWS", key="prev_news") and st.session_state.page_news > 0: 
        st.session_state.page_news -= 1
        st.rerun()
with n2:
    st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>NEWS PAGINA {st.session_state.page_news + 1} DI {total_p_news}</div>", unsafe_allow_html=True)
with n3:
    if st.button("NEXT NEWS >>", key="next_news") and st.session_state.page_news < total_p_news - 1: 
        st.session_state.page_news += 1
        st.rerun()

# --- 2. SOCMINT: TELEGRAM & X ---
st.markdown("<div class='wm-header' style='margin-top: 30px;'>SOCMINT: RAW INTERCEPTS (TG & X)</div>", unsafe_allow_html=True)

socmint_data = fetch_telegram_intel(area_config["tg"]) + fetch_x_intel(area_config.get("x", []))
batch_soc = 6
total_p_soc = max(1, (len(socmint_data) - 1) // batch_soc + 1)
current_soc = socmint_data[st.session_state.page_socmint * batch_soc : (st.session_state.page_socmint + 1) * batch_soc]

if current_soc:
    for i in range(0, len(current_soc), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(current_soc):
                msg = current_soc[i + j]
                with cols[j]:
                    if msg["platform"] == "TG":
                        st.markdown(f"""
                        <div class="tg-card">
                            <div class="card-hdr"><span class="tg-author">@{msg['channel']}</span><span class="tg-badge">TELEGRAM</span></div>
                            <div class="tg-text">{msg['text']}</div>
                            <div class="news-meta" style="margin-top:auto;"><span class="news-time">{msg['time']}</span><a href="{msg['link']}" target="_blank" style="color:#60a5fa; text-decoration:none;">Apri Post >></a></div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="x-card">
                            <div class="card-hdr"><span class="x-author">@{msg['channel']}</span><span class="x-badge">X POST</span></div>
                            <div class="tg-text">{msg['text']}</div>
                            <div class="news-meta" style="margin-top:auto;"><span class="news-time">{msg['time']}</span><a href="{msg['link']}" target="_blank" style="color:#f4f4f5; text-decoration:none;">Apri Post >></a></div>
                        </div>
                        """, unsafe_allow_html=True)
else:
    st.info("Nessuna intercettazione SOCMINT disponibile.")

s1, s2, s3 = st.columns([1, 2, 1])
with s1:
    if st.button("<< PREV SOCMINT", key="prev_soc") and st.session_state.page_socmint > 0: 
        st.session_state.page_socmint -= 1
        st.rerun()
with s2:
    st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>SOCMINT PAGINA {st.session_state.page_socmint + 1} DI {total_p_soc}</div>", unsafe_allow_html=True)
with s3:
    if st.button("NEXT SOCMINT >>", key="next_soc") and st.session_state.page_socmint < total_p_soc - 1: 
        st.session_state.page_socmint += 1
        st.rerun()