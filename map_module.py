import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import requests
import io
import os
import glob
import zipfile
import copy
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

GDELT_DIR = "gdelt_cache"
if not os.path.exists(GDELT_DIR):
    os.makedirs(GDELT_DIR)

@st.cache_data(ttl=900)
def update_and_load_gdelt():
    url_update = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    try:
        resp = requests.get(url_update, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.strip().split('\n')
            export_url = [line.split(' ')[2] for line in lines if 'export.CSV.zip' in line][0]
            filename = export_url.split('/')[-1]
            zip_path = os.path.join(GDELT_DIR, filename)
            csv_filename = filename.replace('.zip', '')
            csv_path = os.path.join(GDELT_DIR, csv_filename)
            
            if not os.path.exists(csv_path):
                r = requests.get(export_url, timeout=15)
                with open(zip_path, 'wb') as f:
                    f.write(r.content)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(GDELT_DIR)
                finally:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
            
            all_csvs = sorted(glob.glob(os.path.join(GDELT_DIR, "*.[cC][sS][vV]")), key=os.path.getmtime, reverse=True)
            for old_file in all_csvs[30:]:
                os.remove(old_file)
    except:
        pass

    all_csvs = glob.glob(os.path.join(GDELT_DIR, "*.[cC][sS][vV]"))
    if not all_csvs: return pd.DataFrame()
    
    df_list = []
    cols = [0, 6, 16, 28, 30, 56, 57, 60]
    names = ['ID', 'ACTOR1', 'ACTOR2', 'ROOTCODE', 'GOLDSTEIN', 'LAT', 'LON', 'URL']
    
    for f in all_csvs[:15]: 
        try:
            temp_df = pd.read_csv(f, sep='\t', header=None, usecols=cols, names=names, on_bad_lines='skip', low_memory=False, dtype=str)
            df_list.append(temp_df)
        except: continue

    if df_list:
        df = pd.concat(df_list, ignore_index=True)
        df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
        df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
        df = df.dropna(subset=['LAT', 'LON'])
        
        df['ROOTCODE'] = pd.to_numeric(df['ROOTCODE'], errors='coerce')
        df = df[df['ROOTCODE'].isin([14, 15, 16, 17, 18, 19, 20])]
        
        if df.empty: return pd.DataFrame()

        df['GOLDSTEIN'] = pd.to_numeric(df['GOLDSTEIN'], errors='coerce').fillna(0)
        df['ACTOR1'] = df['ACTOR1'].fillna('Sconosciuto')
        df['ACTOR2'] = df['ACTOR2'].fillna('Sconosciuto')
        
        def get_color(g):
            if g < -4: return [147, 51, 234, 220]     
            elif g < 0: return [192, 38, 211, 200]   
            elif g == 0: return [156, 163, 175, 100] 
            else: return [37, 99, 235, 200]         
            
        df['color'] = df['GOLDSTEIN'].apply(get_color)
        cameo_map = {14: "Proteste/Tumulti", 15: "Attivita Militare", 16: "Rottura Diplomatica", 17: "Coercizione", 18: "Assalto", 19: "Scontro Armato", 20: "Violenza di Massa"}
        df['EVENT_TYPE'] = df['ROOTCODE'].map(cameo_map).fillna("Evento Ostile")
        
        df["tooltip_text"] = "[GDELT] [ID: " + df["ID"].astype(str) + "]<br>" + df["ACTOR1"] + " -> " + df["EVENT_TYPE"].str.upper() + " -> " + df["ACTOR2"] + "<br>Impatto (Goldstein): " + df["GOLDSTEIN"].astype(str)
        return df
    return pd.DataFrame()

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
def fetch_nasa_firms_48h():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_48h.csv"
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
                df['city'] = cap_names[min_indices]
                df['dist'] = np.round(np.min(distances, axis=1)).astype(int)

                df['acq_date'] = pd.to_datetime(df['acq_date'])
                today = df['acq_date'].max()
                yesterday = today - timedelta(days=1)
                
                fires_today = df[df['acq_date'] == today]['city'].value_counts()
                fires_yesterday = df[df['acq_date'] == yesterday]['city'].value_counts()
                
                delta_stats = []
                for city, count in fires_today.items():
                    prev_count = fires_yesterday.get(city, 0)
                    delta = ((count - prev_count) / prev_count) * 100 if prev_count > 0 else (100.0 if count > 0 else 0.0)
                    delta_stats.append({"city": city, "today": count, "delta": round(delta)})
                
                delta_stats = sorted(delta_stats, key=lambda x: x['today'], reverse=True)
                df_map = df[df['acq_date'] == today].copy()
                df_map["tooltip_text"] = "[TERMICO] Rilevamento Sensori<br>Distanza: " + df_map['dist'].astype(str) + " km da " + df_map['city']
                
                return df_map, delta_stats
        return pd.DataFrame(), []
    except:
        return pd.DataFrame(), []

OPENSKY_USER = "" 
OPENSKY_PASS = ""

@st.cache_data(ttl=30)
def fetch_opensky_flights():
    url = "https://opensky-network.org/api/states/all"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'}
    try:
        if OPENSKY_USER and OPENSKY_PASS:
            resp = requests.get(url, headers=headers, auth=(OPENSKY_USER, OPENSKY_PASS), timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200: return pd.DataFrame()
        
        states = resp.json().get('states', [])
        flights = []
        for s in states:
            if s[5] is not None and s[6] is not None:
                icao = str(s[0]).strip()
                flights.append({"icao": icao, "callsign": str(s[1]).strip() if s[1] else "SCONOSCIUTO", "lon": s[5], "lat": s[6], "alt": int(s[7]) if s[7] else 0, "vel": int(s[9]) if s[9] else 0, "link": f"https://globe.adsbexchange.com/?icao={icao}"})
        df = pd.DataFrame(flights)
        if df.empty: return df
        df["tooltip_text"] = "[RADAR] Volo: " + df["callsign"] + " [" + df["icao"] + "]<br>Alt: " + df["alt"].astype(str) + " m | Vel: " + df["vel"].astype(str) + " m/s"
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=604800) 
def fetch_wri_database():
    url = "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"
    try:
        cols = ['country_long', 'name', 'capacity_mw', 'latitude', 'longitude', 'primary_fuel']
        df = pd.read_csv(url, usecols=cols, low_memory=False)
        df = df.dropna(subset=['latitude', 'longitude'])
        df['capacity_mw'] = df['capacity_mw'].fillna(0).round(1)
        df['primary_fuel'] = df['primary_fuel'].fillna('Sconosciuto')
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_security_advisories():
    adv_map, adv_list = {}, []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get("https://travel.state.gov/_res/rss/TAsTWs.xml", headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for item in soup.find_all('item'):
                title = item.title.text if item.title else ""
                desc = item.description.text if item.description else ""
                level = 4 if "Level 4" in title or "Level 4" in desc else 3 if "Level 3" in title or "Level 3" in desc else 2 if "Level 2" in title or "Level 2" in desc else 1
                country = title.replace("Travel Advisory", "").split("-")[0].strip()
                if level > 1: 
                    adv_map[country] = {"level": level}
                    adv_list.append({"country": country, "source": "USA", "level": level, "title": title, "link": item.link.text if item.link else ""})
    except: pass

    try:
        resp_it = requests.get("https://www.viaggiaresicuri.it/ultima_ora/totale.json", headers=headers, timeout=10)
        if resp_it.status_code == 200:
            for item in resp_it.json()[:15]:
                adv_list.append({"country": item.get('titolo', 'ITA'), "source": "ITA", "level": 3, "title": item.get('testo', '')[:100] + "...", "link": "https://www.viaggiaresicuri.it"})
    except: pass
    return adv_map, adv_list

@st.cache_data(ttl=3600)
def fetch_unhcr_reports():
    url = "https://api.reliefweb.int/v1/reports"
    params = {
        "appname": "osint_terminal",
        "query[value]": "refugees OR displaced",
        "limit": 15,
        "sort[]": "date:desc",
        "profile": "full"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            reports = []
            for d in data:
                fields = d.get('fields', {})
                title = fields.get('title', '')
                date = fields.get('date', {}).get('created', '')[:10]
                link = fields.get('url', '')
                if title:
                    reports.append({"title": title, "date": date, "link": link})
            return reports
    except: pass
    return []

@st.cache_data(ttl=86400)
def fetch_world_geojson():
    try:
        resp = requests.get("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson", timeout=15)
        if resp.status_code == 200: return resp.json()
    except: return None

def render_strategic_map(selected_area, active_layers, selected_countries=None):
    if selected_countries is None: selected_countries = []
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
                feature['properties']['tooltip_text'] = f"[MAPPA] {country_name}\nNessun avviso."
                
                c_name_clean = country_name.lower().replace("republic of ", "").replace("the ", "")
                for adv_country, adv_data in adv_map.items():
                    a_name_clean = adv_country.lower()
                    if a_name_clean in c_name_clean or c_name_clean in a_name_clean:
                        feature['properties']['fill_color'] = [220, 38, 38, 160] if adv_data['level'] == 4 else [249, 115, 22, 140] if adv_data['level'] == 3 else [253, 224, 71, 100]
                        feature['properties']['tooltip_text'] = f"[ALLERTA] {country_name}<br>Livello {adv_data['level']}"
                        break
            layers.append(pdk.Layer("GeoJsonLayer", geojson_data, pickable=True, stroked=True, filled=True, get_fill_color="properties.fill_color", get_line_color=[100, 100, 100, 100], line_width_min_pixels=1))

    if "Eventi GDELT" in active_layers:
        df_gdelt = update_and_load_gdelt()
        if not df_gdelt.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_gdelt, get_position=["LON", "LAT"], get_color="color", get_radius=1500, radius_min_pixels=4, radius_max_pixels=15, pickable=True))

    if "Sensori Termici" in active_layers:
        df_firms, _ = fetch_nasa_firms_48h()
        if not df_firms.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_firms, get_position=["longitude", "latitude"], get_color=[255, 60, 0, 200], get_radius=1000, radius_min_pixels=3, radius_max_pixels=12, pickable=True))

    if "Tracciamento Voli" in active_layers:
        df_flights = fetch_opensky_flights()
        if not df_flights.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_flights, get_position=["lon", "lat"], get_color=[6, 182, 212, 200], get_radius=1000, radius_min_pixels=3, radius_max_pixels=10, pickable=True))

    if "Infrastrutture Energetiche" in active_layers and selected_countries:
        df_energy = fetch_wri_database()
        if not df_energy.empty:
            df_filtered = df_energy[df_energy['country_long'].isin(selected_countries)].copy()
            if not df_filtered.empty:
                df_filtered["icon_data"] = [{"url": "https://img.icons8.com/fluency/512/factory.png", "width": 128, "height": 128, "anchorY": 128}] * len(df_filtered)
                df_filtered["tooltip_text"] = "[INFRA] " + df_filtered["name"] + "<br>Tipo: " + df_filtered["primary_fuel"] + " (" + df_filtered["capacity_mw"].astype(str) + " MW)"
                layers.append(pdk.Layer("IconLayer", data=df_filtered, get_position=["longitude", "latitude"], get_icon="icon_data", get_size=4, size_scale=5, pickable=True))

    geo_views = {"Analisi Globale": {"lat": 20, "lon": 0, "zoom": 1.2}, "Medio Oriente": {"lat": 31, "lon": 42, "zoom": 3.8}, "Europa / NATO": {"lat": 50, "lon": 20, "zoom": 3.2}, "Asia-Pacifico": {"lat": 15, "lon": 115, "zoom": 3.0}, "Americhe": {"lat": 20, "lon": -90, "zoom": 2.2}, "Africa": {"lat": 5, "lon": 20, "zoom": 2.5}}
    v = geo_views.get(selected_area, geo_views["Analisi Globale"])

    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=v["lat"], longitude=v["lon"], zoom=v["zoom"], pitch=45), map_style="dark", tooltip={"html": "{tooltip_text}", "style": {"backgroundColor": "#050505", "color": "#f3f4f6", "border": "1px solid #1f2937"}}))import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import requests
import io
import os
import glob
import zipfile
import copy
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

GDELT_DIR = "gdelt_cache"
if not os.path.exists(GDELT_DIR):
    os.makedirs(GDELT_DIR)

@st.cache_data(ttl=900)
def update_and_load_gdelt():
    url_update = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    try:
        resp = requests.get(url_update, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.strip().split('\n')
            export_url = [line.split(' ')[2] for line in lines if 'export.CSV.zip' in line][0]
            filename = export_url.split('/')[-1]
            zip_path = os.path.join(GDELT_DIR, filename)
            csv_filename = filename.replace('.zip', '')
            csv_path = os.path.join(GDELT_DIR, csv_filename)
            
            if not os.path.exists(csv_path):
                r = requests.get(export_url, timeout=15)
                with open(zip_path, 'wb') as f:
                    f.write(r.content)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(GDELT_DIR)
                finally:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
            
            all_csvs = sorted(glob.glob(os.path.join(GDELT_DIR, "*.[cC][sS][vV]")), key=os.path.getmtime, reverse=True)
            for old_file in all_csvs[30:]:
                os.remove(old_file)
    except:
        pass

    all_csvs = glob.glob(os.path.join(GDELT_DIR, "*.[cC][sS][vV]"))
    if not all_csvs: return pd.DataFrame()
    
    df_list = []
    cols = [0, 6, 16, 28, 30, 56, 57, 60]
    names = ['ID', 'ACTOR1', 'ACTOR2', 'ROOTCODE', 'GOLDSTEIN', 'LAT', 'LON', 'URL']
    
    for f in all_csvs[:15]: 
        try:
            temp_df = pd.read_csv(f, sep='\t', header=None, usecols=cols, names=names, on_bad_lines='skip', low_memory=False, dtype=str)
            df_list.append(temp_df)
        except: continue

    if df_list:
        df = pd.concat(df_list, ignore_index=True)
        df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
        df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
        df = df.dropna(subset=['LAT', 'LON'])
        
        df['ROOTCODE'] = pd.to_numeric(df['ROOTCODE'], errors='coerce')
        df = df[df['ROOTCODE'].isin([14, 15, 16, 17, 18, 19, 20])]
        
        if df.empty: return pd.DataFrame()

        df['GOLDSTEIN'] = pd.to_numeric(df['GOLDSTEIN'], errors='coerce').fillna(0)
        df['ACTOR1'] = df['ACTOR1'].fillna('Sconosciuto')
        df['ACTOR2'] = df['ACTOR2'].fillna('Sconosciuto')
        
        def get_color(g):
            if g < -4: return [147, 51, 234, 220]     
            elif g < 0: return [192, 38, 211, 200]   
            elif g == 0: return [156, 163, 175, 100] 
            else: return [37, 99, 235, 200]         
            
        df['color'] = df['GOLDSTEIN'].apply(get_color)
        cameo_map = {14: "Proteste/Tumulti", 15: "Attivita Militare", 16: "Rottura Diplomatica", 17: "Coercizione", 18: "Assalto", 19: "Scontro Armato", 20: "Violenza di Massa"}
        df['EVENT_TYPE'] = df['ROOTCODE'].map(cameo_map).fillna("Evento Ostile")
        
        df["tooltip_text"] = "[GDELT] [ID: " + df["ID"].astype(str) + "]<br>" + df["ACTOR1"] + " -> " + df["EVENT_TYPE"].str.upper() + " -> " + df["ACTOR2"] + "<br>Impatto (Goldstein): " + df["GOLDSTEIN"].astype(str)
        return df
    return pd.DataFrame()

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
def fetch_nasa_firms_48h():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_48h.csv"
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
                df['city'] = cap_names[min_indices]
                df['dist'] = np.round(np.min(distances, axis=1)).astype(int)

                df['acq_date'] = pd.to_datetime(df['acq_date'])
                today = df['acq_date'].max()
                yesterday = today - timedelta(days=1)
                
                fires_today = df[df['acq_date'] == today]['city'].value_counts()
                fires_yesterday = df[df['acq_date'] == yesterday]['city'].value_counts()
                
                delta_stats = []
                for city, count in fires_today.items():
                    prev_count = fires_yesterday.get(city, 0)
                    delta = ((count - prev_count) / prev_count) * 100 if prev_count > 0 else (100.0 if count > 0 else 0.0)
                    delta_stats.append({"city": city, "today": count, "delta": round(delta)})
                
                delta_stats = sorted(delta_stats, key=lambda x: x['today'], reverse=True)
                df_map = df[df['acq_date'] == today].copy()
                df_map["tooltip_text"] = "[TERMICO] Rilevamento Sensori<br>Distanza: " + df_map['dist'].astype(str) + " km da " + df_map['city']
                
                return df_map, delta_stats
        return pd.DataFrame(), []
    except:
        return pd.DataFrame(), []

OPENSKY_USER = "" 
OPENSKY_PASS = ""

@st.cache_data(ttl=30)
def fetch_opensky_flights():
    url = "https://opensky-network.org/api/states/all"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'}
    try:
        if OPENSKY_USER and OPENSKY_PASS:
            resp = requests.get(url, headers=headers, auth=(OPENSKY_USER, OPENSKY_PASS), timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200: return pd.DataFrame()
        
        states = resp.json().get('states', [])
        flights = []
        for s in states:
            if s[5] is not None and s[6] is not None:
                icao = str(s[0]).strip()
                flights.append({"icao": icao, "callsign": str(s[1]).strip() if s[1] else "UNKNOWN", "lon": s[5], "lat": s[6], "alt": int(s[7]) if s[7] else 0, "vel": int(s[9]) if s[9] else 0, "link": f"https://globe.adsbexchange.com/?icao={icao}"})
        df = pd.DataFrame(flights)
        if df.empty: return df
        df["tooltip_text"] = "[RADAR] Volo: " + df["callsign"] + " [" + df["icao"] + "]<br>Alt: " + df["alt"].astype(str) + " m | Vel: " + df["vel"].astype(str) + " m/s"
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=604800) 
def fetch_wri_database():
    url = "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"
    try:
        cols = ['country_long', 'name', 'capacity_mw', 'latitude', 'longitude', 'primary_fuel']
        df = pd.read_csv(url, usecols=cols, low_memory=False)
        df = df.dropna(subset=['latitude', 'longitude'])
        df['capacity_mw'] = df['capacity_mw'].fillna(0).round(1)
        df['primary_fuel'] = df['primary_fuel'].fillna('Sconosciuto')
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_security_advisories():
    adv_map, adv_list = {}, []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get("https://travel.state.gov/_res/rss/TAsTWs.xml", headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for item in soup.find_all('item'):
                title = item.title.text if item.title else ""
                desc = item.description.text if item.description else ""
                level = 4 if "Level 4" in title or "Level 4" in desc else 3 if "Level 3" in title or "Level 3" in desc else 2 if "Level 2" in title or "Level 2" in desc else 1
                country = title.replace("Travel Advisory", "").split("-")[0].strip()
                if level > 1: 
                    adv_map[country] = {"level": level}
                    adv_list.append({"country": country, "source": "USA", "level": level, "title": title, "link": item.link.text if item.link else ""})
    except: pass

    try:
        resp_it = requests.get("https://www.viaggiaresicuri.it/ultima_ora/totale.json", headers=headers, timeout=10)
        if resp_it.status_code == 200:
            for item in resp_it.json()[:15]:
                adv_list.append({"country": item.get('titolo', 'ITA'), "source": "ITA", "level": 3, "title": item.get('testo', '')[:100] + "...", "link": "https://www.viaggiaresicuri.it"})
    except: pass
    return adv_map, adv_list

@st.cache_data(ttl=3600)
def fetch_unhcr_reports():
    url = "https://api.reliefweb.int/v1/reports"
    params = {
        "appname": "osint_terminal",
        "query[value]": "refugees OR displaced",
        "limit": 15,
        "sort[]": "date:desc",
        "profile": "list"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            reports = []
            for d in data:
                fields = d.get('fields', {})
                reports.append({"title": fields.get('title', ''), "date": fields.get('date', {}).get('created', '')[:10], "link": fields.get('url', '')})
            return reports
    except: pass
    return []

@st.cache_data(ttl=86400)
def fetch_world_geojson():
    try:
        resp = requests.get("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson", timeout=15)
        if resp.status_code == 200: return resp.json()
    except: return None

def render_strategic_map(selected_area, active_layers, selected_countries=None):
    if selected_countries is None: selected_countries = []
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
                feature['properties']['tooltip_text'] = f"[MAPPA] {country_name}\nNessun avviso."
                
                c_name_clean = country_name.lower().replace("republic of ", "").replace("the ", "")
                for adv_country, adv_data in adv_map.items():
                    a_name_clean = adv_country.lower()
                    if a_name_clean in c_name_clean or c_name_clean in a_name_clean:
                        feature['properties']['fill_color'] = [220, 38, 38, 160] if adv_data['level'] == 4 else [249, 115, 22, 140] if adv_data['level'] == 3 else [253, 224, 71, 100]
                        feature['properties']['tooltip_text'] = f"[ALLERTA] {country_name}<br>Livello {adv_data['level']}"
                        break
            layers.append(pdk.Layer("GeoJsonLayer", geojson_data, pickable=True, stroked=True, filled=True, get_fill_color="properties.fill_color", get_line_color=[100, 100, 100, 100], line_width_min_pixels=1))

    if "Eventi GDELT" in active_layers:
        df_gdelt = update_and_load_gdelt()
        if not df_gdelt.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_gdelt, get_position=["LON", "LAT"], get_color="color", get_radius=1500, radius_min_pixels=4, radius_max_pixels=15, pickable=True))

    if "Sensori Termici" in active_layers:
        df_firms, _ = fetch_nasa_firms_48h()
        if not df_firms.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_firms, get_position=["longitude", "latitude"], get_color=[255, 60, 0, 200], get_radius=1000, radius_min_pixels=3, radius_max_pixels=12, pickable=True))

    if "Tracciamento Voli" in active_layers:
        df_flights = fetch_opensky_flights()
        if not df_flights.empty: layers.append(pdk.Layer("ScatterplotLayer", data=df_flights, get_position=["lon", "lat"], get_color=[6, 182, 212, 200], get_radius=1000, radius_min_pixels=3, radius_max_pixels=10, pickable=True))

    if "Infrastrutture Energetiche" in active_layers and selected_countries:
        df_energy = fetch_wri_database()
        if not df_energy.empty:
            df_filtered = df_energy[df_energy['country_long'].isin(selected_countries)].copy()
            if not df_filtered.empty:
                df_filtered["icon_data"] = [{"url": "https://img.icons8.com/fluency/512/factory.png", "width": 128, "height": 128, "anchorY": 128}] * len(df_filtered)
                df_filtered["tooltip_text"] = "[INFRA] " + df_filtered["name"] + "<br>Tipo: " + df_filtered["primary_fuel"] + " (" + df_filtered["capacity_mw"].astype(str) + " MW)"
                layers.append(pdk.Layer("IconLayer", data=df_filtered, get_position=["longitude", "latitude"], get_icon="icon_data", get_size=4, size_scale=5, pickable=True))

    geo_views = {"Analisi Globale": {"lat": 20, "lon": 0, "zoom": 1.2}, "Medio Oriente": {"lat": 31, "lon": 42, "zoom": 3.8}, "Europa / NATO": {"lat": 50, "lon": 20, "zoom": 3.2}, "Asia-Pacifico": {"lat": 15, "lon": 115, "zoom": 3.0}, "Americhe": {"lat": 20, "lon": -90, "zoom": 2.2}, "Africa": {"lat": 5, "lon": 20, "zoom": 2.5}}
    v = geo_views.get(selected_area, geo_views["Analisi Globale"])

    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=v["lat"], longitude=v["lon"], zoom=v["zoom"], pitch=45), map_style="dark", tooltip={"html": "{tooltip_text}", "style": {"backgroundColor": "#14151a", "color": "white", "border": "1px solid #27272a"}}))
