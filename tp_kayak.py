import os
import time
import math
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go


OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '935141faaa6de144edbb5985206038f4')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}

CITIES = [
    'Paris','Marseille','Lyon','Toulouse','Nice','Nantes','Strasbourg','Montpellier','Bordeaux','Lille',
    'Rennes','Reims','Le Havre','Saint-Étienne','Toulon','Angers','Grenoble','Dijon','Nîmes','Aix-en-Provence',
    'Brest','Le Mans','Amiens','Tours','Villeurbanne','Clermont-Ferrand','Limoges','Perpignan','Metz','Besancon',
    'Orleans','Mulhouse','Rouen','Caen','Nancy'
]

CITIES_GEOLOC_CSV = 'cities_geoloc.csv'
WEATHER_DATA_CSV = 'weather_data.csv'
TOP_CITIES_CSV = 'top_cities.csv'
HOTELS_CSV = 'hotels.csv'
HOTELS_WITH_COORDS_CSV = 'hotels_with_coords.csv'
NOMINATIM_DELAY = 1.1
BOOKING_DELAY = 2.0

# def test_openweather_key():
#     """Teste si la clé OpenWeather est valide avec une requête géocodage simple."""
#     test_city = 'Paris'
#     url = 'https://api.openweathermap.org/geo/1.0/direct'
#     params = {'q': f'{test_city},FR', 'limit': 1, 'appid': OPENWEATHER_API_KEY}
#     try:
#         resp = requests.get(url, params=params, timeout=10)
#         if resp.status_code == 200:
#             print("✅ Clé OpenWeather valide.")
#             return True
#         elif resp.status_code == 401:
#             print("❌ Clé OpenWeather invalide ou non activée (401 Unauthorized).")
#             return False
#         else:
#             print(f"⚠️ Erreur inattendue {resp.status_code} lors du test de la clé.")
#             print(resp.text)
#             return False
#     except Exception as e:
#         print(f"❌ Erreur lors du test de la clé OpenWeather : {e}")
#         return False



def geocode_city_openweather(city_name):
    url = 'https://api.openweathermap.org/geo/1.0/direct'
    params = {'q': f'{city_name},FR', 'limit': 1, 'appid': OPENWEATHER_API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None, None
    return data[0]['lat'], data[0]['lon']

def fetch_weather_onecall(lat, lon):
    url = 'https://api.openweathermap.org/data/2.5/onecall'
    params = {
        'lat': lat,
        'lon': lon,
        'exclude': 'minutely,hourly,current,alerts',
        'units': 'metric',
        'appid': OPENWEATHER_API_KEY
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if 'daily' not in data:
        return {'daily': []}
    return {'daily': data['daily'][:7]}



def compute_weather_score(daily_list):
    temps, rain, humidity, clouds, pop = [], [], [], [], []
    for d in daily_list[:7]:
        temps.append(d.get('temp', {}).get('day', None) or (d.get('temp') if isinstance(d.get('temp'), (int,float)) else None))
        rain.append(d.get('rain', 0) or 0)
        humidity.append(d.get('humidity', 50))
        clouds.append(d.get('clouds', 0))
        pop.append(d.get('pop', 0))

    t_mean = sum([t for t in temps if t is not None]) / len([t for t in temps if t is not None])
    rain_mean = sum(rain) / len(rain)
    hum_mean = sum(humidity) / len(humidity)
    pop_mean = sum(pop) / len(pop)
    clouds_mean = sum(clouds) / len(clouds)

    temp_score = max(0, 10 - abs(t_mean - 22) * 0.6)
    rain_score = max(0, 10 - rain_mean * 2)
    hum_score = max(0, 10 - (hum_mean - 50) * 0.08)
    pop_score = max(0, 10 - pop_mean * 8)
    cloud_score = max(0, 10 - clouds_mean * 0.06)

    weather_score = (0.35 * temp_score + 0.25 * rain_score + 0.15 * hum_score + 0.15 * pop_score + 0.10 * cloud_score)
    weather_score = max(0, min(10, weather_score))

    return {
        'score': round(weather_score, 2),
        't_mean': round(t_mean,1),
        'rain_mean': round(rain_mean,2),
        'hum_mean': round(hum_mean,1),
        'pop_mean': round(pop_mean,2),
        'clouds_mean': round(clouds_mean,1)
    }


def scrape_booking_hotels(city_name, n_hotels=5):
    hotels = []
    query = city_name.replace(' ', '+') + '+France'
    url = f'https://www.booking.com/searchresults.html?ss={query}&rows={n_hotels}&nflt=review_score%3D0'
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Erreur scraping Booking pour {city_name} : status {resp.status_code}")
        return hotels
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = soup.select('div[data-testid="property-card"]') or soup.select('.sr_property_block')

    for r in results[:n_hotels]:
        name_tag = r.select_one('div[data-testid="title"]') or r.select_one('.sr-hotel__name')
        name = name_tag.get_text(strip=True) if name_tag else None
        score_tag = r.select_one('div[data-testid="review-score"]') or r.select_one('.bui-review-score__badge')
        score = None
        if score_tag:
            try:
                score = float(score_tag.get_text(strip=True).replace(',', '.'))
            except:
                score = None
        if name:
            hotels.append({'city': city_name, 'hotel_name': name, 'rating': score})
    time.sleep(BOOKING_DELAY)
    return hotels


def geocode_nominatim(query):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': query, 'format': 'json', 'addressdetails': 0, 'limit': 1}
    resp = requests.get(url, params=params, headers={'User-Agent': HEADERS['User-Agent']})
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None, None
    return float(data[0]['lat']), float(data[0]['lon'])


def plot_top_cities_map(df_top):
    fig = px.scatter_mapbox(df_top, lat='lat', lon='lon', hover_name='city', size='score', zoom=5,
                            hover_data={'score':True, 't_mean':True, 'rain_mean':True, 'hum_mean':True},
                            size_max=18, mapbox_style='open-street-map')
    fig.update_layout(title='Top-5 destinations météo (7 jours)')
    fig.write_image("mapweather.png")
    fig.show()


def plot_hotels_map(hotels_df, weather_df_top):
    def make_hover(row):
        city = row['city']
        w = weather_df_top.loc[weather_df_top['city']==city].iloc[0]
        hover = f"🌆 {city}<br>☀️ Score météo: {w['score']}<br>Temp moy: {w['t_mean']}°C | Hum: {w['hum_mean']}% | Pluie moy: {w['rain_mean']} mm<br><br>🏨 {row['hotel_name']} ({row['rating']})"
        return hover

    hotels_df['hover'] = hotels_df.apply(make_hover, axis=1)
    fig = px.scatter_mapbox(hotels_df, lat='latitude', lon='longitude', hover_name='hotel_name', hover_data=['hover'], zoom=5, mapbox_style='open-street-map')
    fig.update_traces(marker=dict(size=10))
    fig.update_layout(title='Hôtels des Top-5 villes')
    fig.write_image("maphotels.png")
    fig.show()


def main():
    if OPENWEATHER_API_KEY == 'VOTRE_CLE_OPENWEATHER_ICI' or not OPENWEATHER_API_KEY:
        print('ERREUR : veuillez définir la variable OPENWEATHER_API_KEY avant d\'exécuter le script.')
        return

    print('Étape 1 – Géolocalisation des villes...')
    rows = []
    for city in tqdm(CITIES):
        try:
            lat, lon = geocode_city_openweather(city)
        except Exception as e:
            print(f'Erreur géocodage {city}: {e}')
            lat, lon = None, None
        rows.append({'city': city, 'lat': lat, 'lon': lon})
        time.sleep(0.1)
    df_cities = pd.DataFrame(rows)
    df_cities.to_csv(CITIES_GEOLOC_CSV, index=False)

    print('Étape 2 – Récupération des prévisions météo (7 jours) et calcul du score)...')
    weather_rows = []
    for _, r in tqdm(df_cities.iterrows(), total=df_cities.shape[0]):
        city, lat, lon = r['city'], r['lat'], r['lon']
        if pd.isna(lat) or pd.isna(lon):
            print(f"⚠️ {city} ignorée (pas de géolocalisation)")
            continue
        try:
            data = fetch_weather_onecall(lat, lon)
            daily = data.get('daily', [])
            if not daily:
                print(f"⚠️ Pas de données météo pour {city}")
                continue
            metrics = compute_weather_score(daily)
            weather_rows.append({**{'city': city, 'lat': lat, 'lon': lon}, **metrics})
        except requests.HTTPError as e:
            print(f'Erreur météo pour {city}: {e}')
        except Exception as e:
            print(f'Erreur inattendue pour {city}: {e}')
        time.sleep(0.2)

    df_weather = pd.DataFrame(weather_rows)
    if df_weather.empty:
        print("❌ Aucune donnée météo récupérée. Vérifiez votre clé OpenWeather et la connexion Internet.")
        return

    df_weather.to_csv(WEATHER_DATA_CSV, index=False)

    print('Étape 3 – Sélection du Top-5 villes selon score météo...')
    df_top5 = df_weather.sort_values(by='score', ascending=False).head(5).reset_index(drop=True)
    df_top5.to_csv(TOP_CITIES_CSV, index=False)
    print('Top-5 :\n', df_top5[['city','score']])

    print('Étape 4 – Affichage et sauvegarde carte Plotly des Top-5 villes...')
    plot_top_cities_map(df_top5)

    print('Étape 5 – Scraping des hôtels depuis Booking.com pour chaque Top-5...')
    hotels_all = []
    for city in df_top5['city']:
        try:
            hotels = scrape_booking_hotels(city, n_hotels=5)
            hotels_all.extend(hotels)
        except Exception as e:
            print(f'Erreur scraping pour {city}: {e}')
    df_hotels = pd.DataFrame(hotels_all)
    if df_hotels.empty:
        print("⚠️ Aucun hôtel récupéré. Vérifiez le scraping ou la connexion.")
    df_hotels.to_csv(HOTELS_CSV, index=False)

    print('Étape 6 – Géocodage des hôtels via Nominatim...')
    hotels_with_coords = []
    for _, row in tqdm(df_hotels.iterrows(), total=df_hotels.shape[0]):
        city, hotel, rating = row['city'], row['hotel_name'], row['rating']
        query = f"{hotel}, {city}, France"
        try:
            lat, lon = geocode_nominatim(query)
        except Exception as e:
            print(f'Erreur Nominatim pour {hotel}: {e}')
            lat, lon = None, None
        hotels_with_coords.append({'city': city, 'hotel_name': hotel, 'rating': rating, 'latitude': lat, 'longitude': lon})
        time.sleep(NOMINATIM_DELAY)

    df_hotels_coords = pd.DataFrame(hotels_with_coords)
    df_hotels_coords.to_csv(HOTELS_WITH_COORDS_CSV, index=False)

    print('Étape 7 – Affichage et sauvegarde carte Plotly des hôtels (Top-5 villes)...')
    weather_top = df_top5[['city','score','t_mean','rain_mean','hum_mean']].copy()
    plot_hotels_map(df_hotels_coords.dropna(subset=['latitude','longitude']), weather_top)

    print('--- Tâche terminée. Vérifiez les fichiers CSV et les images PNG générées (mapweather.png, maphotels.png).')


if __name__ == '__main__':
    main()
