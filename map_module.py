import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import requests
import io
import copy
from bs4 import BeautifulSoup

@st.cache_data(ttl=86400)
def fetch_world_capitals():
    fallback = [("Mosca", 55.75, 37.61), ("Kyiv", 50.45, 30.52), ("Washington", 38.89, -77.03), ("Pechino", 39.90, 116.40)]
    try:
        resp = requests.get("https://restcountries.com/v3.1/all?fields=name,capital,capitalInfo", timeout=10)
        if resp.status_code == 200:
            capitals = []
            for country in resp.json():
                if country.get("capital") and country.get("capitalInfo", {}).get("latlng"):
                    capitals.append((country["capital"][0], country["capitalInfo"]["latlng"][0], country["capitalInfo"]["latlng"][1]))
            return capitals if capitals else fallback
        return fallback
    except:
        return fallback

@st.cache_data(ttl=600)
def fetch_nasa_firms():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            if not df.empty and 'latitude' in df.columns:
                df = df[['latitude', 'longitude', 'bright_ti4', 'acq_date', 'acq_time']]
                capitals = fetch_world_capitals()
                cap_names = np.array([c[0] for c in capitals])
                cap_lats = np.radians([c[1] for c in capitals])
                cap_lons = np.radians([c[2] for c in capitals])
                
                fire_lats = np.radians(df['latitude'].values)[:, np.newaxis]
                fire_lons = np.radians(df['longitude'].values)[:, np.newaxis]
                
                dlat = cap_lats - fire_lats
                dlon = cap_lons - fire_lons
                a = np.sin(dlat/2)**2 + np.cos(fire_lats) * np.cos(cap_lats) * np.sin(dlon/2)**2
                distances = 6371 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                
                min_indices = np.argmin(distances, axis=1)
                min_distances = np.min(distances, axis=1)
                
                df['city'] = cap_names[min_indices]
                df['dist'] = np.round(min_distances).astype(int)
                df["tooltip_text"] = (
                    "<b>Rilevamento Termico (VIIRS)</b><br>"
                    "Data: " + df["acq_date"].astype(str) + " " + df["acq_time"].astype(str) + "<br>"
                    "Distanza: " + df['dist'].astype(str) + " km da " + df['city']
                )
                return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# SE STREAMLIT CLOUD VIENE BLOCCATO, CREA UN ACCOUNT GRATIS SU OPENSKY NETWORK 
# E INSERISCI QUI USERNAME E PASSWORD PER SBLOCCARE I VOLI
OPENSKY_USER = "" 
OPENSKY_PASS = ""

@st.cache_data(ttl=30)
def fetch_opensky_flights():
    url = "https://opensky-network.org/api/states/all"
    
    # Mascheriamo la richiesta per ingannare i filtri del server Cloud
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        if OPENSKY_USER and OPENSKY_PASS:
            resp = requests.get(url, headers=headers, auth=(OPENSKY_USER, OPENSKY_PASS), timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
            
        if resp.status_code != 200: 
            return pd.DataFrame()
            
        states = resp.json().get('states', [])
        flights = []
        for s in states:
            if s[5] is not None and s[6] is not None:
                icao = str(s[0]).strip()
                flights.append({
                    "icao": icao, "callsign": str(s[1]).strip() if s[1] else "UNKNOWN",
                    "lon": s[5], "lat": s[6], "alt": int(s[7]) if s[7] else 0,
                    "vel": int(s[9]) if s[9] else 0,
                    "link": f"https://globe.adsbexchange.com/?icao={icao}"
                })
        df = pd.DataFrame(flights)
        if df.empty: return df

        df["tooltip_text"] = "<b>Volo:</b> " + df["callsign"] + " [" + df["icao"] + "]<br><b>Alt:</b> " + df["alt"].astype(str) + " m | <b>Vel:</b> " + df["vel"].astype(str) + " m/s"
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_energy_infra():
    data = [
        {"name": "Zaporizhzhia NPP", "lat": 47.51, "lon": 34.58, "type": "Nucleare (Ucraina)"},
        {"name": "Kursk NPP", "lat": 51.67, "lon": 35.60, "type": "Nucleare (Russia)"},
        {"name": "Abqaiq Refinery", "lat": 25.93, "lon": 49.68, "type": "Petrolio (Saudi Aramco)"},
        {"name": "Natanz Enrichment Facility", "lat": 33.72, "lon": 51.72, "type": "Sito Nucleare (Iran)"},
        {"name": "Kharg Island Terminal", "lat": 29.24, "lon": 50.32, "type": "Export Petrolio (Iran)"},
        {"name": "Stretto di Hormuz", "lat": 26.56, "lon": 56.25, "type": "Transito Navale Critico"}
    ]
    df = pd.DataFrame(data)
    df["icon_data"] = [{"url": "https://img.icons8.com/fluency/512/factory.png", "width": 128, "height": 128, "anchorY": 128}] * len(df)
    df["tooltip_text"] = "<b>" + df["name"] + "</b><br>Tipo: " + df["type"]
    return df

@st.cache_data(ttl=3600)
def fetch_security_advisories():
    adv_map = {}
    adv_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'}
    
    try:
        resp = requests.get("https://travel.state.gov/_res/rss/TAsTWs.xml", headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for item in soup.find_all('item'):
                title = item.title.text if item.title else ""
                desc = item.description.text if item.description else ""
                link = item.link.text if item.link else ""
                
                level = 1
                if "Level 4" in title or "Level 4" in desc: level = 4
                elif "Level 3" in title or "Level 3" in desc: level = 3
                elif "Level 2" in title or "Level 2" in desc: level = 2

                country = title.replace("Travel Advisory", "").split("-")[0].strip()
                if level > 1: 
                    adv_map[country] = {"level": level}
                    adv_list.append({"country": country, "source": "USA", "level": level, "title": title, "link": link})
    except: pass

    try:
        resp_it = requests.get("https://www.viaggiaresicuri.it/ultima_ora/totale.json", headers=headers, timeout=10)
        if resp_it.status_code == 200:
            data = resp_it.json()
            for item in data[:15]:
                adv_list.append({
                    "country": item.get('titolo', 'Avviso ITA'),
                    "source": "ITA", "level": 3,
                    "title": item.get('testo', '')[:100] + "...",
                    "link": "https://www.viaggiaresicuri.it"
                })
    except: pass

    return adv_map, adv_list

@st.cache_data(ttl=86400)
def fetch_world_geojson():
    url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except: return None

def render_strategic_map(selected_area, active_layers):
    layers = []
    
    if "Avvisi Sicurezza" in active_layers:
        adv_map, _ = fetch_security_advisories()
        geojson_cache = fetch_world_geojson()
        
        if geojson_cache and adv_map:
            geojson_data = copy.deepcopy(geojson_cache)
            for feature in geojson_data['features']:
                props = feature.get('properties', {})
                country_name = props.get('ADMIN', props.get('name', 'Sconosciuto'))
                
                feature['properties']['fill_color'] = [30, 30, 30, 80] 
                feature['properties']['tooltip_text'] = f"{country_name}\nNessun avviso."
                
                c_name_clean = country_name.lower().replace("republic of ", "").replace("the ", "")
                for adv_country, adv_data in adv_map.items():
                    a_name_clean = adv_country.lower()
                    if a_name_clean in c_name_clean or c_name_clean in a_name_clean:
                        if adv_data['level'] == 4:
                            feature['properties']['fill_color'] = [220, 38, 38, 160] 
                        elif adv_data['level'] == 3:
                            feature['properties']['fill_color'] = [249, 115, 22, 140] 
                        elif adv_data['level'] == 2:
                            feature['properties']['fill_color'] = [253, 224, 71, 100] 
                        
                        feature['properties']['tooltip_text'] = f"<b>{country_name}</b><br>Allerta Sicurezza: Livello {adv_data['level']}"
                        break
            
            layers.append(pdk.Layer(
                "GeoJsonLayer", geojson_data, pickable=True, stroked=True, filled=True,
                get_fill_color="properties.fill_color", get_line_color=[100, 100, 100, 100], line_width_min_pixels=1,
            ))

    if "Sensori Termici" in active_layers:
        df_firms = fetch_nasa_firms()
        if not df_firms.empty:
            layers.append(pdk.Layer("ScatterplotLayer", data=df_firms, get_position=["longitude", "latitude"],
                                    get_color=[255, 60, 0, 200], get_radius=15000, pickable=True))

    if "Tracciamento Voli" in active_layers:
        df_flights = fetch_opensky_flights()
        if not df_flights.empty:
            layers.append(pdk.Layer("ScatterplotLayer", data=df_flights, get_position=["lon", "lat"],
                                    get_color=[6, 182, 212, 200], get_radius=8000, pickable=True))

    if "Infrastrutture Energetiche" in active_layers:
        df_energy = fetch_energy_infra()
        if not df_energy.empty:
            layers.append(pdk.Layer("IconLayer", data=df_energy, get_position=["lon", "lat"], get_icon="icon_data",
                                    get_size=5, size_scale=5, pickable=True))

    geo_views = {
        "Analisi Globale": {"lat": 20, "lon": 0, "zoom": 1.2}, "Medio Oriente": {"lat": 31, "lon": 42, "zoom": 3.8},
        "Europa / NATO": {"lat": 50, "lon": 20, "zoom": 3.2}, "Asia-Pacifico": {"lat": 15, "lon": 115, "zoom": 3.0},
        "Americhe": {"lat": 20, "lon": -90, "zoom": 2.2}, "Africa": {"lat": 5, "lon": 20, "zoom": 2.5}
    }
    v = geo_views.get(selected_area, geo_views["Analisi Globale"])

    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=v["lat"], longitude=v["lon"], zoom=v["zoom"], pitch=45),
        map_style="dark",
        tooltip={"html": "{tooltip_text}", "style": {"backgroundColor": "#14151a", "color": "white", "border": "1px solid #27272a"}}
    ))
