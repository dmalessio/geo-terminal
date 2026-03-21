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

st.set_page_config(layout="wide", page_title="STRATEGIC TERMINAL v13.2", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0b0c10; color: #f4f4f5; }
    .block-container { padding-top: 1rem !important; max-width: 98%; }
    [data-testid="stSidebar"] { background-color: #121214 !important; border-right: 1px solid #27272a; }
    [data-testid="stSidebar"] .css-17lntkn { color: #f4f4f5; font-weight: 700; letter-spacing: 1px;}
    div[data-baseweb="select"] > div { background-color: #0b0c10; border: 1px solid #27272a; color: #4ade80; font-weight: bold; }
    div[data-baseweb="select"] > div:hover { border-color: #4ade80; }
    
    .wm-header { color: #f4f4f5; font-size: 1rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; border-bottom: 1px solid #27272a; padding-bottom: 10px; }
    .wm-card { background-color: #14151a; border: 1px solid #23252d; border-radius: 4px; padding: 10px; height: 185px; margin-bottom: 10px; display: flex; flex-direction: column; }
    .tg-card, .x-card { border-radius: 4px; padding: 10px; height: 160px; margin-bottom: 10px; display: flex; flex-direction: column; overflow: hidden; }
    .tg-card { background-color: #1a1e24; border: 1px solid #3b82f6; border-left: 4px solid #3b82f6; }
    .x-card { background-color: #121214; border: 1px solid #3f3f46; border-left: 4px solid #f4f4f5; }
    
    .tg-author, .x-author { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;}
    .tg-author { color: #60a5fa; } .x-author { color: #f4f4f5; }
    .tg-text { color: #e2e8f0; font-size: 0.8rem; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; margin-bottom: auto;}
    
    .card-hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .card-lbl { color: #64748b; font-size: 0.6rem; font-weight: 800; text-transform: uppercase; }
    
    .live-badge, .tg-badge, .x-badge { font-size: 0.55rem; padding: 2px 6px; font-weight: 700; border-radius: 2px; }
    .live-badge { color: #4ade80; border: 1px solid #4ade80; background-color: rgba(74,222,128,0.05); }
    .tg-badge { color: #3b82f6; border: 1px solid #3b82f6; background-color: rgba(59,130,246,0.05); }
    .x-badge { color: #f4f4f5; border: 1px solid #f4f4f5; background-color: rgba(244,244,245,0.05); }
    
    .news-meta { display: flex; justify-content: space-between; font-size: 0.65rem; font-weight: 700; margin-bottom: 4px; }
    .news-src { color: #fbbf24; text-transform: uppercase; }
    .news-time { color: #94a3b8; font-weight: 400; font-size: 0.65rem; }
    .news-title { color: #e2e8f0; font-size: 0.85rem; font-weight: 600; line-height: 1.3; margin-bottom: 5px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
    .news-smry { color: #94a3b8; font-size: 0.75rem; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    
    .eco-widget { background: #121214; border: 1px solid #27272a; border-radius: 4px; padding: 8px; height: 70px; display: flex; flex-direction: column; justify-content: center;}
    .eco-label { color: #a1a1aa; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; margin-bottom: 2px;}
    .eco-value { color: #f4f4f5; font-size: 1.1rem; font-weight: 700; }
    .eco-sym { color: #4ade80; font-size: 0.8rem; margin-right: 2px; }
    .delta-pos { color: #ef4444; font-size: 0.8rem; } 
    .delta-neg { color: #4ade80; font-size: 0.8rem; }
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
                        results.append({"channel": acc, "text": BeautifulSoup(item.summary, 'html.parser').get_text(separator=" ", strip=True), "time": "X Post", "link": item.link, "platform": "X"})
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
            
            processed.append({
                'title': clean_title,
                'link': item.link if hasattr(item, 'link') else "#",
                'source': item.source.title if hasattr(item, 'source') and hasattr(item.source, 'title') else 'INTEL SOURCE',
                'dt': dt,
                'display_time': dt.strftime("%H:%M - %d/%m/%Y"),
                'summary': clean_summary
            })
        processed.sort(key=lambda x: x['dt'], reverse=True)
        return processed
    except:
        return []

@st.cache_data(ttl=600)
def get_manifold_predictions(keywords):
    try:
        resp = requests.get("https://api.manifold.markets/v0/search-markets", params={"filter": "open", "sort": "liquidity", "limit": 300}, timeout=10)
        results = []
        for m in resp.json():
            q, prob = m.get('question', '').lower(), m.get('probability')
            if prob is not None and any(re.search(r'\b' + re.escape(k) + r'\b', q) for k in keywords):
                results.append({"t": m.get('question')[:90], "o": f"{prob*100:.0f}%"})
        return results[:8]
    except: return []

for key in ['page_news', 'page_socmint', 'page_adv']:
    if key not in st.session_state: st.session_state[key] = 0

with st.sidebar:
    st.title("INTEL CONTROL")
    area = st.selectbox("Scenario Focus", list(SCENARIOS.keys()))
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
    
    if st.button("Forza Aggiornamento Mappa"):
        map_module.fetch_opensky_flights.clear()
        map_module.update_and_load_gdelt.clear()
        map_module.fetch_nasa_firms_48h.clear()
        st.rerun()
        
    active_layers = [l for l, c in zip(["Eventi GDELT", "Sensori Termici", "Tracciamento Voli", "Infrastrutture Energetiche", "Avvisi Sicurezza"], [layer_gdelt, layer_thermal, layer_flights, layer_energy, layer_advisory]) if c]

st.markdown("<div class='wm-header'>SITUATIONAL AWARENESS MAP (24H SENSING)</div>", unsafe_allow_html=True)
map_module.render_strategic_map(area, active_layers, selected_countries)

if "Eventi GDELT" in active_layers:
    df_gdelt = map_module.update_and_load_gdelt()
    if not df_gdelt.empty:
        with st.expander("[DATABASE] EVENTI GDELT (Cerca ID)", expanded=False):
            st.dataframe(df_gdelt[['ID', 'ACTOR1', 'EVENT_TYPE', 'ACTOR2', 'GOLDSTEIN', 'URL']], column_config={"URL": st.column_config.LinkColumn("Fonte Notizia", display_text="Apri Fonte")}, hide_index=True, use_container_width=True)

reports = map_module.fetch_unhcr_reports()
if reports:
    with st.expander("[SFOLLATI] FLUSSI MIGRATORI (ReliefWeb)", expanded=False):
        st.dataframe(pd.DataFrame(reports), column_config={"link": st.column_config.LinkColumn("Report Completo", display_text="Apri Report")}, hide_index=True, use_container_width=True)

if "Infrastrutture Energetiche" in active_layers and selected_countries:
    df_energy = map_module.fetch_wri_database()
    if not df_energy.empty:
        df_filtered = df_energy[df_energy['country_long'].isin(selected_countries)]
        if not df_filtered.empty:
            with st.expander("[INFRA] INFRASTRUTTURE STRATEGICHE (WRI Database)", expanded=False):
                st.dataframe(
                    df_filtered[['country_long', 'name', 'primary_fuel', 'capacity_mw']].sort_values('capacity_mw', ascending=False),
                    column_config={"country_long": "Nazione", "name": "Impianto", "primary_fuel": "Fonte", "capacity_mw": "Capacità (MW)"},
                    hide_index=True, use_container_width=True
                )

if "Tracciamento Voli" in active_layers:
    df_flights = map_module.fetch_opensky_flights()
    if not df_flights.empty:
        with st.expander("[RADAR] REGISTRO VOLI ATTIVI", expanded=False):
            st.dataframe(df_flights[['callsign', 'icao', 'alt', 'vel', 'link']], column_config={"link": st.column_config.LinkColumn("Link Tracker", display_text="Traccia su ADSBExchange")}, hide_index=True, use_container_width=True)

if adv_list := map_module.fetch_security_advisories()[1]:
    with st.expander("[ALLERTA] REGISTRO AVVISI DI SICUREZZA (USA E ITA)", expanded=False):
        batch_adv, total_p_adv = 4, max(1, (len(adv_list) - 1) // 4 + 1)
        current_adv = adv_list[st.session_state.page_adv * batch_adv : (st.session_state.page_adv + 1) * batch_adv]
        cols = st.columns(4)
        for j, item in enumerate(current_adv):
            color = "#ef4444" if item['level'] == 4 else "#f97316" if item['level'] == 3 else "#fde047"
            with cols[j]:
                st.markdown(f"""
                <div style="background-color: #14151a; border: 1px solid {color}; border-left: 4px solid {color}; padding: 10px; border-radius: 4px; margin-bottom: 10px; height: 140px; display: flex; flex-direction: column;">
                    <div style="font-size: 0.65rem; font-weight: 800; color: {color}; margin-bottom: 3px;">{item['source']} | LVL {item['level']}</div>
                    <div style="color: #f4f4f5; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item['country']}</div>
                    <div style="color: #94a3b8; font-size: 0.75rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{item['title']}</div>
                    <a href="{item['link']}" target="_blank" style="color:#60a5fa; text-decoration:none; font-size:0.65rem; margin-top:auto;">Apri Fonte</a>
                </div>
                """, unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1, 2, 1])
        with a1:
            if st.button("PREV", key="prev_adv") and st.session_state.page_adv > 0: st.session_state.page_adv -= 1; st.rerun()
        with a2: st.markdown(f"<div style='text-align:center; font-size:0.65rem; color:#64748b; margin-top:10px;'>PAG. {st.session_state.page_adv + 1}/{total_p_adv}</div>", unsafe_allow_html=True)
        with a3:
            if st.button("NEXT", key="next_adv") and st.session_state.page_adv < total_p_adv - 1: st.session_state.page_adv += 1; st.rerun()

st.write("")
m_cols = st.columns(6)
assets = [("BRENT OIL", "BZ=F", "$"), ("GOLD", "GC=F", "$"), ("DOLLAR IDX", "DX-Y.NYB", "Pts")]
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

st.markdown(f"<div class='wm-header' style='margin-top: 20px;'>TERMINALE OPERATIVO: {area.upper()}</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
area_config = SCENARIOS[area]
news = fetch_sorted_news(area_config["rss"])
forecasts = get_manifold_predictions(area_config["kws"])

batch_news, total_p_news = 9, max(1, (len(news) - 1) // 9 + 1)
current_news = news[st.session_state.page_news * batch_news : (st.session_state.page_news + 1) * batch_news]

def draw_news(item):
    smry = item.get('summary', '')[:100] + "..."
    tit = item.get('title', '')[:80] + "..."
    src = item.get('source', 'INTEL SOURCE')
    lnk = item.get('link', '#')
    dt = item.get('display_time', '')
    return f"""<div class="wm-card"><div class="card-hdr"><span class="card-lbl">{area}</span><div class="live-badge">LIVE</div></div><div class="news-meta"><span class="news-src">{src}</span><span class="news-time">{dt}</span></div><div class="news-title">{tit}</div><div class="news-smry">{smry}</div><a href="{lnk}" target="_blank" style="color:#4ade80; text-decoration:none; font-size:0.65rem; margin-top:auto;">Apri Analisi</a></div>"""

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
                with st.container(border=True): st.markdown(f"<span style='color:#4ade80; font-weight:700; font-size:1.1rem;'>{f['o']}</span><br><span style='font-size:0.75rem; color:#d4d4d8;'>{f['t']}</span>", unsafe_allow_html=True)
        else: st.info("Nessuna previsione rilevata.")

n1, n2, n3 = st.columns([1, 2, 1])
with n1:
    if st.button("PREV NEWS", key="prev_news") and st.session_state.page_news > 0: st.session_state.page_news -= 1; st.rerun()
with n2: st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>NEWS PAGINA {st.session_state.page_news + 1} DI {total_p_news}</div>", unsafe_allow_html=True)
with n3:
    if st.button("NEXT NEWS", key="next_news") and st.session_state.page_news < total_p_news - 1: st.session_state.page_news += 1; st.rerun()

st.markdown("<div class='wm-header' style='margin-top: 30px;'>SOCMINT: RAW INTERCEPTS (TG E X)</div>", unsafe_allow_html=True)
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
                    c_class, badge = ("tg-card", "TELEGRAM") if msg["platform"] == "TG" else ("x-card", "X POST")
                    c_author = "tg-author" if msg["platform"] == "TG" else "x-author"
                    st.markdown(f"""<div class="{c_class}"><div class="card-hdr"><span class="{c_author}">@{msg['channel']}</span><span class="x-badge">{badge}</span></div><div class="tg-text">{msg['text']}</div><div class="news-meta" style="margin-top:auto;"><span class="news-time">{msg['time']}</span><a href="{msg['link']}" target="_blank" style="color:#60a5fa; text-decoration:none;">Apri Post</a></div></div>""", unsafe_allow_html=True)
else: st.info("Nessuna intercettazione SOCMINT disponibile.")

s1, s2, s3 = st.columns([1, 2, 1])
with s1:
    if st.button("PREV SOCMINT", key="prev_soc") and st.session_state.page_socmint > 0: st.session_state.page_socmint -= 1; st.rerun()
with s2: st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:10px;'>SOCMINT PAGINA {st.session_state.page_socmint + 1} DI {total_p_soc}</div>", unsafe_allow_html=True)
with s3:
    if st.button("NEXT SOCMINT", key="next_soc") and st.session_state.page_socmint < total_p_soc - 1: st.session_state.page_socmint += 1; st.rerun()
