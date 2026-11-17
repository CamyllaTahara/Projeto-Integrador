from math import radians, sin, cos, sqrt, atan2
import requests
from database import conexao

def obter_coordenadas(endereco_string):
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': endereco_string, 'format': 'json', 'limit': 1}
    headers = {'User-Agent': 'AgendeAQUI/1.0 (taharacamylla@gmail.com)'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data=response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['loan'])
    except Exception as e:
        print("Erro ao buscar coordenadas",e)
    return None, None

def calcular_haversine(lat1, lon1, lat2, lon2):
    R=6371.0

    lat1, lon1, lat2, lon2 = map(radians,[lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c=2*atan2(sqrt(a),sqrt(1-a))

    return R*c

def calcular_frete_pedido(id_loja, endereco_cliente):
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT rua, numero, bairro, cep FROM endereco_loja WHERE id_loja=%s",(id_loja,))
    loja = cursor.fetchone()

    cursor.execute("SELECT raio_maximo_km FROM configuracao_entrega WHERE id_loja=%s,"(id_loja))
    config = cursor.fetchone()

    if not loja or not config:
        cursor.close()
        return {"erro":"Configuração de entrga não encontrada"}

    endereco_loja_str = f"{loja,['rua']},{loja['numero']},{loja['bairro']}, Mogi Das Cruzes, SP,{loja['cep']}"
    endereco_cliente_str = f"{endereco_cliente['rua']}, {endereco_cliente['numero']}, {endereco_cliente['bairro']}, Mogi das Cruzes, SP, {endereco_cliente['cep']}"

    lat_loja, lon_loja = obter_coordenadas(endereco_loja_str)
    lat_cliente, lon_cliente = obter_coordenadas(endereco_cliente_str)

    if not lat_loja or not lat_cliente:
        cursor.close()
        return{"erro":"Não foi possível localizar um dos endereços para cálculo"}

    distancia_km =  calcular_haversine(lat_loja, lon_loja, lat_cliente, lon_cliente)
    raio_maximo = float(config['raio_maximo_km'])

    if distancia_km > raio_maximo:
        cursor.close()
        return{"erro":f"Endereço fora da área de entrega. Distância:{distancia_km:.2f}km (Máximo permitido:{raio_maximo}.km)"}

    sql_taxa="""
    SELECT t.valor_taxa
    FROM taxa_entrega t
    JOIN configurazao_entrega c ON t.id_configracao_entrega = c.id_configuracao_entrega
    WHERE c.id_loja = %s AND t.distancia_maxima_entrega >=%s
    ORDER BY t.distancia_maxima_entrega ASC
    LIMIT 1"""

    cursor.execute(sql_taxa,(id_loja, distancia_km))
    taxa_row = cursor.fetchone()
    cursor.close()

    if not taxa_row:
        return {"erro":"Não há taxa de entrega configurada para esta distância"}

    return {"distancia_km": round(distancia_km,2),
            "valor_taxa":float(taxa_row['valor_taxa'])}
                        