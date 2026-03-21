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

st.set_page_config(layout="wide", page_title="STRATEGIC TERMINAL v14.2", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f3f4f6; }
    .block-container { padding-top: 3rem !important; max-width: 98%; }
    [data-testid="stSidebar"] { background-color: #0e1117 !important; border-right: 1px solid #1f2937; }
    [data-testid="stSidebar"] .css-17lntkn { color: #f3f4f6; font-weight: 700; letter-spacing: 1px;}
    div[data-baseweb="select"] > div { background-color: #050505; border: 1px solid #1f2937; color: #06b6d4; font-weight: bold; }
    div[data-baseweb="select"] > div:hover { border-color: #06b6d4; }
    
    .wm-header { color: #f3f4f6; font-size: 0.9rem; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 15px; border-bottom: 1px solid #1f2937; padding-bottom: 8px; }
    
    .wm-card { background-color: rgba(14, 17, 23, 0.7); backdrop-filter: blur(10px); border: 1px solid #1f2937; border-radius: 6px; padding: 12px; height: 185px; margin-bottom: 12px; display: flex; flex-direction: column; }
    .tg-card, .x-card { background-color: rgba(14, 17, 23, 0.7); backdrop-filter: blur(10px); border-radius: 6px; padding: 12px; height: 160px; margin-bottom: 12px; display: flex; flex-direction: column; overflow: hidden; }
    .tg-card { border: 1px solid #1f2937; border-left: 4px solid #3b82f6; }
    .x-card { border: 1px solid #1f2937; border-left: 4px solid #f3f4f6; }
    
    .tg-author, .x-author { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;}
    .tg-author { color: #3b82f6; } .x-author { color: #f3f4f6; }
    .tg-text { color: #d1d5db; font-size: 0.8rem; line-height: 1.4; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; margin-bottom: auto;}
    
    .card-hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .card-lbl { color: #9ca3af; font-size: 0.6rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    
    .live-badge, .tg-badge, .x-badge { font-size: 0.55rem; padding: 2px 6px; font-weight: 700; border-radius: 2px; }
    .live-badge { color: #06b6d4; border: 1px solid #06b6d4; background-color: rgba(6,182,212,0.1); }
    .tg-badge { color: #3b82f6; border: 1px solid #3b82f6; background-color: rgba(59,130,246,0.1); }
    .x-badge { color: #f3f4f6; border: 1px solid #f3f4f6; background-color: rgba(243,244,246,0.1); }
    
    .news-meta { display: flex; justify-content: space-between; font-size: 0.65rem; font-weight: 700; margin-bottom: 6px; }
    .news-src { color: #f59e0b; text-transform: uppercase; }
    .news-time { color: #6b7280; font-weight: 400; font-size: 0.65rem; }
    .news-title { color: #f3f4f6; font-size: 0.85rem; font-weight: 600; line-height: 1.3; margin-bottom: 6px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
    .news-smry { color: #9ca3af; font-size: 0.75rem; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    
    .eco-widget { background: rgba(14, 17, 23, 0.7); backdrop-filter: blur(10px); border: 1px solid #1f2937; border-radius: 6px; padding: 10px; height: 75px; display: flex; flex-direction: column; justify-content: center;}
    .eco-label { color: #9ca3af; font-size: 0.6rem; font-weight: 800; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 1px;}
    .eco-value { color: #f3f4f6; font-size: 1.2rem; font-weight: 700; }
    .eco-sym { color: #06b6d4; font-size: 0.8rem; margin-right: 4px; }
    .delta-pos { color: #ef4444; font-size: 0.8rem; } 
    .delta-neg { color: #22c55e; font-size: 0.8rem; }
    
    .feed-card { background: rgba(14, 17, 23, 0.5); border-left: 3px solid #38bdf8; padding: 10px; margin-bottom: 10px; border-radius: 4px; border-top: 1px solid #1f2937; border-right: 1px solid #1f2937; border-bottom: 1px solid #1f2937; }
    .feed-hdr { display: flex; justify-content: space-between; font-size: 0.65rem; font-weight: 800; color: #9ca3af; margin-bottom: 4px; text-transform: uppercase;}
    .feed-title { font-size: 0.8rem; font-weight: 600; color: #f3f4f6; line-height: 1.2; margin-bottom: 4px;}
    .feed-meta { font-size: 0.7rem; color: #6b7280; display: flex; justify-content: space-between;}
    .feed-link { color: #06b6d4; text-decoration: none; font-weight: 600; }
    .feed-link:hover { color: #38bdf8; text-decoration: underline; }
    
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] { scrollbar-width: thin; scrollbar-color: #1f2937 #050505; }
    div[data-testid="stTabs"] button { color: #9ca3af; font-weight: 600; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #06b6d4; border-bottom-color: #06b6d4; }
    </style>
    """, unsafe_allow_html=True)

SCENARIOS = {
    "Analisi Globale": {
        "rss": '("geopolitics" OR "national security" OR "intelligence report" OR "military conflict") when:24h',
        "kws": ["geopolitics", "military", "war"], 
        "tg": ["geopolitics_live", "disclosetv"], 
        "x": ["OSINTdefender"]
    },
    "Medio Oriente": {
        "rss": '("Israel" OR "Iran" OR "Gaza" OR "Hezbollah" OR "Houthis" OR "Red Sea") AND ("attack" OR "escalation" OR "missile" OR "clash") when:24h',
        "kws": ["israel", "iran", "gaza"], 
        "tg": ["Middle_East_Spectator", "FarsNewsInt", "me_observer_TG", "warfareanalysis", "FotrosResistancee", "thecradlemedia"], 
        "x": ["Faytuks"]
    },
    "Europa / NATO": {
        "rss": '("Ukraine" OR "Russia" OR "NATO" OR "European defense") AND ("frontline" OR "offensive" OR "sanctions" OR "missile") when:24h',
        "kws": ["ukraine", "russia", "nato"], 
        "tg": ["liveukraine_media", "DDGeopolitics"], 
        "x": ["Tendar"]
    },
    "Asia-Pacifico": {
        "rss": '("Taiwan" OR "China" OR "South China Sea" OR "North Korea") AND ("military exercise" OR "invasion" OR "threat" OR "US Navy") when:24h',
        "kws": ["taiwan", "china", "korea"], 
        "tg": ["CCTV_english"], 
        "x": ["IndoPac_Info"]
    },
    "Americhe": {
        "rss": '("USA" OR "Latin America" OR "South America") AND ("investigation" OR "sanctions" OR "corruption" OR "cartel" OR "crisis" OR "White House") when:24h',
        "kws": ["usa", "election", "security"], 
        "tg": ["disclosetv"], 
        "x": ["visegrad24"]
    },
    "Africa": {
        "rss": '("Sahel" OR "Sudan" OR "Congo" OR "Ethiopia") AND ("coup" OR "civil war" OR "militia" OR "terrorism") when:24h',
        "kws": ["africa", "sudan", "sahel"], 
        "tg": ["africaintel"], 
        "x": ["CasusBellii"]
    }
}

BOUNDING_BOXES = {
    "Analisi Globale": None,
    "Medio Oriente": {"lat_min": 12, "lat_max": 45, "lon_min": 26, "lon_max": 65},
    "Europa / NATO": {"lat_min": 35, "lat_max": 75, "lon_min": -15, "lon_max": 45},
    "Asia-Pacifico": {"lat_min": -10, "lat_max": 55, "lon_min": 60, "lon_max": 180},
    "Americhe": {"lat_min": -55, "lat_max": 75, "lon_min": -170, "lon_max": -30},
    "Africa": {"lat_min": -35, "lat_max": 37, "lon_min": -20, "lon_max": 55}
}

@st.cache_data(ttl=180)
def fetch_telegram_intel(channels):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for channel in channels:
        try:
            resp = requests.get(f"https://t.me/s/{channel}", headers=headers, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            messages, dates = soup.find_all('div', class_='tgme_widget_message_text'), soup.find_all('time', class_='time')
            for msg, date in zip(messages[-15:], dates[-15:]):
                clean_text = msg.get_text(separator=" ", strip=True)
                if len(clean_text) > 20: results.append({"channel": channel, "text": clean_text, "time": date.text, "link": f"https://t.me/{channel}", "platform": "TG"})
        except: continue
    return list(reversed(results))

@st.cache_data(ttl=300)
def fetch_x_intel(accounts):
    results = []
    bridges = ["https://nitter.poast.org", "https://nitter.privacydev.net"]
    for acc in accounts:
        for bridge in bridges:
            try:
                feed = feedparser.parse(f"{bridge}/{acc}/rss")
                if feed.entries:
                    for item in feed.entries[:5]:
                        results.append({"channel": acc, "text": BeautifulSoup(item.summary, 'html.parser').get_text(separator=" ", strip=True), "time": "POST X", "link": item.link, "platform": "X"})
                    break
            except: pass
    return results

@st.cache_data(ttl=300)
def fetch_sorted_news(q):
    encoded_q = requests.utils.quote(q)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url).entries
        processed = []
        seen = set()
        for item in feed:
            title = item.title if hasattr(item, 'title') else ""
            clean_title = title.split(' - ')[0].strip()
            if clean_title.lower() in seen: continue
            seen.add(clean_title.lower())
            dt = datetime.fromtimestamp(mktime(item.published_parsed)) if hasattr(item, 'published_parsed') and item.published_parsed else datetime.now()
            summary_raw = item.summary if hasattr(item, 'summary') else ""
            clean_summary = BeautifulSoup(summary_raw, 'html.parser').get_text(separator=" ", strip=True)
            processed.append({'title': clean_title, 'link': item.link if hasattr(item, 'link') else "#", 'source': item.source.title if hasattr(item, 'source') and hasattr(item.source, 'title') else 'FONTE INTEL', 'dt': dt, 'display_time': dt.strftime("%H:%M - %d/%m/%Y"), 'summary': clean_summary})
        processed.sort(key=lambda x: x['dt'], reverse=True)
        return processed
    except: return []

@st.cache_data(ttl=600)
def get_manifold_predictions(keywords):
    try:
        resp = requests.get("https://api.manifold.markets/v0/search-markets", params={"filter": "open", "sort": "liquidity", "limit": 500}, timeout=10)
        results = []
        for m in resp.json():
            q, prob = m.get('question', '').lower(), m.get('probability')
            if prob is not None and any(re.search(r'\b' + re.escape(k) + r'\b', q) for k in keywords):
                results.append({"t": m.get('question')[:100], "o": f"{prob*100:.0f}%"})
        return results[:15]
    except: return []

for key in ['page_news', 'page_socmint']:
    if key not in st.session_state: st.session_state[key] = 0

with st.sidebar:
    st.title("CONTROLLO INTEL")
    area = st.selectbox("Focus Scenario", list(SCENARIOS.keys()))
    st.divider()
    st.markdown("**LIVELLI MAPPA (SENSING)**")
    layer_gdelt = st.checkbox("Eventi GDELT (Live DB)", value=True)
    layer_thermal = st.checkbox("Sensori Termici (NASA 48h)", value=True)
    layer_flights = st.checkbox("Tracciamento Voli (OpenSky)", value=False)
    layer_energy = st.checkbox("Infrastrutture Strategiche", value=True)
    selected_countries = []
    if layer_energy:
        df_energy_all = map_module.fetch_wri_database()
        if not df_energy_all.empty:
            country_list = sorted(df_energy_all['country_long'].dropna().unique().tolist())
            selected_countries = st.multiselect("Seleziona Nazioni (WRI DB)", country_list, default=[])
    layer_advisory = st.checkbox("Avvisi Sicurezza (USA/ITA)", value=True)
    
    if st.button("Forza Aggiornamento Mappa", use_container_width=True):
        map_module.fetch_opensky_flights.clear()
        map_module.update_and_load_gdelt.clear()
        map_module.fetch_nasa_firms_48h.clear()
        st.rerun()
        
    active_layers = [l for l, c in zip(["Eventi GDELT", "Sensori Termici", "Tracciamento Voli", "Infrastrutture Energetiche", "Avvisi Sicurezza"], [layer_gdelt, layer_thermal, layer_flights, layer_energy, layer_advisory]) if c]

m_cols = st.columns(6)
assets = [("BRENT OIL", "BZ=F", "$"), ("ORO", "GC=F", "$"), ("INDICE DOLLARO", "DX-Y.NYB", "Pts")]
for i, (name, tick, sym) in enumerate(assets):
    with m_cols[i]:
        try:
            val = yf.Ticker(tick).fast_info['last_price']
            st.markdown(f'<div class="eco-widget"><div class="eco-label">{name}</div><div class="eco-value"><span class="eco-sym">{sym}</span>{val:.2f}</div></div>', unsafe_allow_html=True)
        except: st.markdown(f'<div class="eco-widget">{name}<br>N/A</div>', unsafe_allow_html=True)

_, nasa_stats = map_module.fetch_nasa_firms_48h()
for i in range(3):
    with m_cols[i+3]:
        if i < len(nasa_stats):
            stat = nasa_stats[i]
            d_class, d_sym = ("delta-pos", "(+)") if stat['delta'] > 0 else ("delta-neg", "(-)")
            st.markdown(f'<div class="eco-widget"><div class="eco-label">FUOCHI: {stat["city"][:12]}</div><div class="eco-value">{stat["today"]} <span class="{d_class}">{d_sym} {abs(stat["delta"])}% (24h)</span></div></div>', unsafe_allow_html=True)

st.write("")
col_map, col_feed = st.columns([2.8, 1.2])

with col_map:
    st.markdown("<div class='wm-header'>MAPPA DI SITUATIONAL AWARENESS (SENSING 24H)</div>", unsafe_allow_html=True)
    map_module.render_strategic_map(area, active_layers, selected_countries)

with col_feed:
    st.markdown("<div class='wm-header'>FLUSSO INTEL IN TEMPO REALE</div>", unsafe_allow_html=True)
    tab_gdelt, tab_unhcr, tab_adv, tab_voli = st.tabs(["GDELT", "SFOLLATI", "ALLERTE", "VOLI"])
    
    with tab_gdelt:
        with st.container(height=450, border=False):
            if "Eventi GDELT" in active_layers:
                df_gdelt = map_module.update_and_load_gdelt()
                if not df_gdelt.empty:
                    
                    box = BOUNDING_BOXES.get(area)
                    if box:
                        df_gdelt = df_gdelt[(df_gdelt['LAT'] >= box['lat_min']) & (df_gdelt['LAT'] <= box['lat_max']) & (df_gdelt['LON'] >= box['lon_min']) & (df_gdelt['LON'] <= box['lon_max'])]

                    search_gdelt = st.text_input("🔍 Cerca ID Evento (Es. 123456)", key="search_gdelt").strip()
                    if search_gdelt:
                        df_gdelt = df_gdelt[df_gdelt['ID'].astype(str).str.contains(search_gdelt)]
                        
                    if not df_gdelt.empty:
                        html_gdelt = ""
                        for _, row in df_gdelt.head(50).iterrows():
                            html_gdelt += f"""
                            <div class='feed-card' style='border-left-color: #a855f7;'>
                                <div class='feed-hdr'><span style='color:#a855f7;'>GDELT</span> <span>ID: {row['ID']}</span></div>
                                <div class='feed-title'>{row['ACTOR1']} ➔ {row['EVENT_TYPE']} ➔ {row['ACTOR2']}</div>
                                <div class='feed-meta'><span>Goldstein: {row['GOLDSTEIN']}</span> <a class='feed-link' href='{row['URL']}' target='_blank'>FONTE ↗</a></div>
                            </div>
                            """
                        st.markdown(html_gdelt, unsafe_allow_html=True)
                    else: st.info("Nessun evento GDELT corrisponde ai filtri.")
                else: st.info("Nessun evento GDELT rilevato.")
            else: st.warning("Layer GDELT disattivato sulla mappa.")

    with tab_unhcr:
        with st.container(height=450, border=False):
            reports = map_module.fetch_unhcr_reports()
            if reports:
                html_unhcr = ""
                for r in reports:
                    html_unhcr += f"""
                    <div class='feed-card' style='border-left-color: #3b82f6;'>
                        <div class='feed-hdr'><span style='color:#3b82f6;'>RELIEFWEB</span> <span>{r['date']}</span></div>
                        <div class='feed-title'>{r['title']}</div>
                        <div class='feed-meta'><span>UNHCR / OCHA</span> <a class='feed-link' href='{r['link']}' target='_blank'>REPORT ↗</a></div>
                    </div>
                    """
                st.markdown(html_unhcr, unsafe_allow_html=True)
            else: st.info("Nessun report umanitario recente rilevato.")

    with tab_adv:
        with st.container(height=450, border=False):
            _, adv_list = map_module.fetch_security_advisories()
            if adv_list:
                html_adv = ""
                for a in adv_list:
                    border_color = "#ef4444" if a['level'] == 4 else "#f59e0b" if a['level'] == 3 else "#eab308"
                    html_adv += f"""
                    <div class='feed-card' style='border-left-color: {border_color};'>
                        <div class='feed-hdr'><span style='color:{border_color};'>{a['source']} LVL {a['level']}</span> <span>{a['country']}</span></div>
                        <div class='feed-title'>{a['title']}</div>
                        <div class='feed-meta'><span>Avviso di Sicurezza</span> <a class='feed-link' href='{a['link']}' target='_blank'>LEGGI ↗</a></div>
                    </div>
                    """
                st.markdown(html_adv, unsafe_allow_html=True)
            else: st.info("Nessun avviso di sicurezza critico.")

    with tab_voli:
        with st.container(height=450, border=False):
            if "Tracciamento Voli" in active_layers:
                df_flights = map_module.fetch_opensky_flights()
                if not df_flights.empty:
                    search_volo = st.text_input("🔍 Cerca Volo (ICAO/Callsign)", key="search_volo").strip().upper()
                    if search_volo:
                        df_flights = df_flights[df_flights['icao'].str.upper().str.contains(search_volo) | df_flights['callsign'].str.upper().str.contains(search_volo)]
                    
                    if not df_flights.empty:
                        html_voli = ""
                        for _, r in df_flights.head(50).iterrows():
                            html_voli += f"""
                            <div class='feed-card' style='border-left-color: #06b6d4;'>
                                <div class='feed-hdr'><span style='color:#06b6d4;'>RADAR</span> <span>ICAO: {r['icao']}</span></div>
                                <div class='feed-title'>VOLO: {r['callsign']}</div>
                                <div class='feed-meta'><span>Alt: {r['alt']}m | Vel: {r['vel']}m/s</span> <a class='feed-link' href='{r['link']}' target='_blank'>TRACCIA ↗</a></div>
                            </div>
                            """
                        st.markdown(html_voli, unsafe_allow_html=True)
                    else: st.info("Nessun volo corrisponde alla ricerca.")
                else: st.info("Nessun volo rilevato in questa area.")
            else: st.warning("Layer Voli disattivato sulla mappa.")

st.markdown(f"<div class='wm-header' style='margin-top: 30px;'>TERMINALE OPERATIVO: {area.upper()}</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
area_config = SCENARIOS[area]
news = fetch_sorted_news(area_config["rss"])
forecasts = get_manifold_predictions(area_config["kws"])

batch_news, total_p_news = 9, max(1, (len(news) - 1) // 9 + 1)
current_news = news[st.session_state.page_news * batch_news : (st.session_state.page_news + 1) * batch_news]

def draw_news(item):
    smry = item.get('summary', '')[:100] + "..."
    tit = item.get('title', '')[:80] + "..."
    src = item.get('source', 'FONTE INTEL')
    lnk = item.get('link', '#')
    dt = item.get('display_time', '')
    return f"""<div class="wm-card"><div class="card-hdr"><span class="card-lbl">{area}</span><div class="live-badge">DIRETTA</div></div><div class="news-meta"><span class="news-src">{src}</span><span class="news-time">{dt}</span></div><div class="news-title">{tit}</div><div class="news-smry">{smry}</div><a href="{lnk}" target="_blank" style="color:#06b6d4; text-decoration:none; font-size:0.65rem; margin-top:auto; font-weight:600;">Apri Analisi ↗</a></div>"""

with c1:
    for item in current_news[0:3]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c2:
    for item in current_news[3:6]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c3:
    for item in current_news[6:9]: st.markdown(draw_news(item), unsafe_allow_html=True)
with c4:
    st.markdown("<div class='card-lbl' style='margin-bottom:10px;'>Previsioni (Sentiment)</div>", unsafe_allow_html=True)
    with st.container(height=580, border=False):
        if forecasts:
            for f in forecasts:
                with st.container(border=True): st.markdown(f"<span style='color:#06b6d4; font-weight:700; font-size:1.1rem;'>{f['o']}</span><br><span style='font-size:0.75rem; color:#d1d5db;'>{f['t']}</span>", unsafe_allow_html=True)
        else: st.info("Nessuna previsione rilevata.")

n1, n2, n3 = st.columns([1, 2, 1])
with n1:
    if st.button("PRECEDENTE", key="prev_news", use_container_width=True) and st.session_state.page_news > 0: st.session_state.page_news -= 1; st.rerun()
with n2: st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>NOTIZIE PAG. {st.session_state.page_news + 1} DI {total_p_news}</div>", unsafe_allow_html=True)
with n3:
    if st.button("SUCCESSIVA", key="next_news", use_container_width=True) and st.session_state.page_news < total_p_news - 1: st.session_state.page_news += 1; st.rerun()

st.markdown("<div class='wm-header' style='margin-top: 30px;'>SOCMINT: INTERCETTAZIONI GREZZE (TG E X)</div>", unsafe_allow_html=True)
socmint_data = fetch_telegram_intel(area_config["tg"]) + fetch_x_intel(area_config.get("x", []))
batch_soc, total_p_soc = 6, max(1, (len(socmint_data) - 1) // 6 + 1)
current_soc = socmint_data[st.session_state.page_socmint * batch_soc : (st.session_state.page_socmint + 1) * batch_soc]

if current_soc:
    for i in range(0, len(current_soc), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(current_soc):
                msg = current_soc[i + j]
                with cols[j]:
                    c_class, badge = ("tg-card", "TELEGRAM") if msg["platform"] == "TG" else ("x-card", "POST X")
                    c_author = "tg-author" if msg["platform"] == "TG" else "x-author"
                    st.markdown(f"""<div class="{c_class}"><div class="card-hdr"><span class="{c_author}">@{msg['channel']}</span><span class="x-badge">{badge}</span></div><div class="tg-text">{msg['text']}</div><div class="news-meta" style="margin-top:auto;"><span class="news-time">{msg['time']}</span><a href="{msg['link']}" target="_blank" style="color:#06b6d4; text-decoration:none; font-weight:600;">Apri Post ↗</a></div></div>""", unsafe_allow_html=True)
else: st.info("Nessuna intercettazione SOCMINT disponibile.")

s1, s2, s3 = st.columns([1, 2, 1])
with s1:
    if st.button("PRECEDENTE", key="prev_soc", use_container_width=True) and st.session_state.page_socmint > 0: st.session_state.page_socmint -= 1; st.rerun()
with s2: st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>SOCMINT PAG. {st.session_state.page_socmint + 1} DI {total_p_soc}</div>", unsafe_allow_html=True)
with s3:
    if st.button("SUCCESSIVA", key="next_soc", use_container_width=True) and st.session_state.page_socmint < total_p_soc - 1: st.session_state.page_socmint += 1; st.rerun()