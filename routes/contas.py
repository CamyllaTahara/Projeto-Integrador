import math
import requests

def obter_coordenadas(endereco_str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': endereco_str,
        'format': 'json',
        'limit': 1
    }
 
    headers = {'User-Agent': 'MeuSistemaDelivery/1.0'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200 and response.json():
            dados = response.json()[0]
            return float(dados['lat']), float(dados['lon'])
    except Exception as e:
        print("Erro ao buscar coordenadas:", e)
    
    return None, None

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula a distância em quilômetros entre dois pontos usando a fórmula de Haversine."""
    R = 6371.0  
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon / 2) ** 2)
         
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c