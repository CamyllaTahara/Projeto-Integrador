from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, request, session, url_for
from database import conexao
import time
from routes.contas import obter_coordenadas, calcular_distancia_km
import math
publico_bp=Blueprint("publico", __name__)


@publico_bp.route("/cardapio/<int:id_loja>")
def cardapio_publico(id_loja):
    cursor = conexao.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT * FROM produto WHERE id_loja = %s AND ativo = 1", (id_loja,))
    loja=cursor.fetchone()

    if not loja:
        return 'Loja não encontrada'

    sql_produtos = """
    SELECT p.*, f.caminho_foto, v.caminho_video,
    COALESCE(SUM(ip.quantidade),0) as total_vendido
    FROM produto p
    LEFT JOIN foto_produto f ON p.id_produto = f.id_produto
    LEFT JOIN video_produto v ON p.id_produto = v.id_produto
    LEFT JOIN item_pedido ip ON p.id_produto = ip.id_produto
    LEFT JOIN pedido ped ON ip.id_pedido = ped.id_pedido 
        AND ped.data_pedido >= p.data_reposicao
    WHERE p.id_loja = %s AND p.ativo = 1
    GROUP BY p.id_produto
    """

    cursor.execute(sql_produtos, (id_loja,))
    produtos_brutos = cursor.fetchall()

    cursor.close()

    produtos = []
    for p in produtos_brutos:
        if p.get('ativo', 1) == 0:
            continue

        estoque_total = p['estoque'] if p['estoque'] is not None else 10
        total_vendido = p['total_vendido'] if p['total_vendido'] is not None else 0

        p['estoque_disponivel'] = estoque_total - total_vendido
        
        if p['estoque_disponivel'] <= 0:
            continue

        produtos.append(p)

    return render_template("publico/cardapio.html", loja=loja, produtos=produtos)


@publico_bp.route("/carrinho/adicionar/<int:id_produto>", methods=["GET", "POST"])
def adicionar_carrinho(id_produto):

    if "carrinho" not in session:
        session["carrinho"] = {}

    quantidade = int(request.values.get("quantidade", 1))
    print(f"--- DEBUG: O que veio do formulário ('quantidade') = {quantidade}")

    if quantidade <= 0:
        return "Quantidade Inválida"

    cursor = conexao.cursor(dictionary=True, buffered=True)

    sql = "SELECT id_produto, id_loja, nome_produto, preco, estoque FROM produto WHERE id_produto=%s"
    cursor.execute(sql, (id_produto,))
    produto = cursor.fetchone()



    if not produto:
        cursor.close()
        return "Produto não encontrado"

    session["id_loja"] = produto["id_loja"]


    cursor.execute("""
        SELECT COALESCE(SUM(IP.quantidade), 0) as total_vendido
        FROM item_pedido IP
        WHERE IP.id_produto = %s
    """, (id_produto,))
    
    venda_info = cursor.fetchone()
    cursor.close()

     
  

    total_vendido = venda_info['total_vendido'] if venda_info and venda_info['total_vendido'] is not None else 0
    estoque_total = produto['estoque'] if produto['estoque'] is not None else 10


    estoque_disponivel = estoque_total - total_vendido

    print(f"--- DEBUG ESTOQUE ---")
    print(f"Produto: {produto['nome_produto']}")
    print(f"Estoque Total cadastrado no banco: {estoque_total}")
    print(f"Total já vendido (item_pedido): {total_vendido}")
    print(f"Estoque Disponível calculado: {estoque_disponivel}")
    print(f"---------------------")



    id_str = str(id_produto)
    quantidade_atual_no_carrinho = 0
    if id_str in session["carrinho"]:
        quantidade_atual_no_carrinho = session["carrinho"][id_str]["quantidade"]

    quantidade_total_desejada = quantidade_atual_no_carrinho + quantidade

   
    if quantidade_total_desejada > estoque_disponivel:
        return f"Ops! A quantidade desejada ({quantidade_total_desejada}) ultrapassa o nosso estoque disponível ({estoque_disponivel} unidades)."

    if id_str in session["carrinho"]:
        session["carrinho"][id_str]["quantidade"] = quantidade_total_desejada
    else:
        session["carrinho"][id_str] = {
            "nome": produto["nome_produto"],
            "preco": float(produto["preco"]),
            "quantidade": quantidade
        }

    session.modified = True

    return redirect(url_for("publico.ver_carrinho", id_loja=produto["id_loja"]))

@publico_bp.route("/carrinho", methods = ["GET","POST"])
def ver_carrinho():

    carrinho = session.get("carrinho",{})

    total_geral = 0

    for id_produto, item in carrinho.items():
        subtotal = item["preco"] * item ["quantidade"]
        item ["subtotal"] = subtotal
        total_geral += subtotal

    id_loja = session.get("id_loja", 1)

    return render_template("publico/carrinho.html",carrinho=carrinho, total_geral=total_geral, id_loja=id_loja)


@publico_bp.route("/carrinho/remover/<id_produto>", methods = ["GET"])
def remover_carrinho(id_produto):

    if "carrinho" in session:

        if id_produto in session["carrinho"]:
            del session["carrinho"][id_produto]
            session.modified = True

            return redirect(url_for("publico.ver_carrinho"))




@publico_bp.route("/carrinho/limpar", methods=["GET"])
def limpar_carrinho():
    session.pop("carrinho", None)
    return redirect(url_for("publico.ver_carrinho"))

@publico_bp.route("/escolher_modalidade", methods=["GET", "POST"])
def escolher_modalidade():
    id_loja = session.get("id_loja")
    if not id_loja:
        return redirect(url_for("publico.cardapio_publico", id_loja = 1))

    cursor = conexao.cursor(dictionary=True, buffered=True)

    sql = """SELECT ce.permite_entrega, ce.permite_retirada, ce.raio_maximo_km,
    el.rua, el.numero, el.bairro, el.cep,el.complemento, el.referencia
    FROM configuracao_entrega ce
    LEFT JOIN endereco_loja el ON ce.id_loja = el.id_loja
    WHERE ce.id_loja = %s"""

    cursor.execute(sql, (id_loja,))
    config_loja = cursor.fetchone()
    cursor.close()

    if not config_loja:
        return "Configuração da loja não encontrada."

    if request.method=="POST":
        modalidade =  request.form.get("modalidade")
        session["modalidade"] = modalidade


        if modalidade not in ["entrega", "retirada"]:
            return "Por favor, selecione uma modalidade válida."

        if modalidade=="retirada":
            session["taxa_entrega"] = 0
            session.pop("id_endereco_entrega", None)
            session.pop("endereco_entrega",None)

            return redirect(url_for("publico.agendamento_data_hora"))

        return redirect(url_for("publico.endereco_entrega"))
   
    

    return render_template("publico/escolher_modalidade.html", config_loja=config_loja)

from .contas import obter_coordenadas, calcular_distancia_km 
import math


@publico_bp.route("/endereco_entrega", methods=["GET", "POST"])
def endereco_entrega():

    print("DEBUG - Modalidade na session:", session.get("modalidade"))
    print("DEBUG - Todos os dados da session:", dict(session))

    if session.get("modalidade") != "entrega":
        return redirect(url_for("publico.escolher_modalidade"))

    id_cliente = session.get("id_cliente")

    cursor = conexao.cursor(dictionary=True, buffered=True)

    if request.method == "POST":

        acao = request.form.get("acao")

        if acao == "usar_existente":

            id_endereco_existente = request.form.get("id_endereco_existente")

            if not id_endereco_existente:
                cursor.close()
                return "Selecione um endereço existente."

            cursor.execute("""
                SELECT *
                FROM endereco_cliente
                WHERE id_endereco_cliente = %s
                AND id_cliente = %s
            """, (id_endereco_existente, id_cliente))

            endereco_obj = cursor.fetchone()

            if not endereco_obj:
                cursor.close()
                return "Endereço não encontrado."

            session["id_endereco_entrega"] = endereco_obj["id_endereco_cliente"]

            session["endereco_entrega"] = {
                "cep": endereco_obj["cep"],
                "rua": endereco_obj["rua"],
                "numero": endereco_obj["numero"],
                "bairro": endereco_obj["bairro"],
                "complemento": endereco_obj["complemento"],
                "referencia": endereco_obj["referencia"]
            }

            cursor.close()
            return redirect(url_for("publico.agendamento_data_hora"))

        elif acao == "cadastrar_novo":

            cep = request.form.get("cep", "").strip()
            rua = request.form.get("rua", "").strip()
            numero = request.form.get("numero", "").strip()
            bairro = request.form.get("bairro", "").strip()
            complemento = request.form.get("complemento", "").strip()
            referencia = request.form.get("referencia", "").strip()

            if not cep or not rua or not numero or not bairro:
                cursor.close()
                return "Preencha todos os campos obrigatórios."

            id_loja = session.get("id_loja", 13)

            cursor.execute(
                "SELECT * FROM endereco_loja WHERE id_loja = %s",
                (id_loja,)
            )
            endereco_loja = cursor.fetchone()

            cursor.execute("""
                SELECT raio_maximo_km
                FROM configuracao_entrega
                WHERE id_loja = %s
                LIMIT 1
            """, (id_loja,))

            config_entrega = cursor.fetchone()

            raio_maximo = (
                float(config_entrega["raio_maximo_km"])
                if config_entrega and config_entrega.get("raio_maximo_km")
                else 20.0
            )

            cursor.close()

            str_end_loja = (
                f"{endereco_loja.get('rua')}, "
                f"{endereco_loja.get('numero')}, "
                f"{endereco_loja.get('bairro')}"
            ) if endereco_loja else ""

            str_end_cliente = f"{rua}, {numero}, {bairro}"

            lat_loja, lon_loja = obter_coordenadas(str_end_loja) if str_end_loja else (None, None)
            lat_cliente, lon_cliente = obter_coordenadas(str_end_cliente)

            distancia_km = 0.0

            if lat_loja is not None and lon_loja is not None and lat_cliente is not None and lon_cliente is not None:
                distancia_km = calcular_distancia_km(
                    lat_loja, lon_loja,
                    lat_cliente, lon_cliente
                )

            if distancia_km > raio_maximo:
                return (
                    f"Desculpe, o seu endereço está a aproximadamente "
                    f"{distancia_km:.1f} km da nossa loja. "
                    f"Nosso raio máximo de entrega é de {raio_maximo:.1f} km. "
                    f"Você pode retirar seu pedido na loja, selecionando a opção Retirada."
                )

            cursor = conexao.cursor()

            sql = """
                INSERT INTO endereco_cliente
                (id_cliente, cep, rua, numero, bairro, complemento, referencia)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                sql,
                (id_cliente, cep, rua, numero, bairro, complemento, referencia)
            )

            conexao.commit()

            session["id_endereco_entrega"] = cursor.lastrowid

            session["endereco_entrega"] = {
                "cep": cep,
                "rua": rua,
                "numero": numero,
                "bairro": bairro,
                "complemento": complemento,
                "referencia": referencia
            }

            cursor.close()

            return redirect(url_for("publico.agendamento_data_hora"))

        cursor.close()
        return "Ação inválida."

    sql_enderecos = """
        SELECT MIN(id_endereco_cliente) AS id_endereco_cliente,
               cep, rua, numero, bairro, complemento, referencia
        FROM endereco_cliente
        WHERE id_cliente = %s
        GROUP BY cep, rua, numero, bairro, complemento, referencia
        ORDER BY id_endereco_cliente DESC
    """

    cursor.execute(sql_enderecos, (id_cliente,))
    enderecos_salvos = cursor.fetchall()

    print("DEBUG - Endereços encontrados no banco:", enderecos_salvos)

    cursor.close()

    return render_template(
        "publico/endereco_entrega.html",
        enderecos_salvos=enderecos_salvos
    )

@publico_bp.route("/agendamento_data_hora", methods=["GET","POST"])
def agendamento_data_hora():

    if "modalidade" not in session:
        return redirect(url_for("publico.escolher_modalidade"))

    id_loja = session.get("id_loja", 13)  

    if request.method == "POST":
        id_disponibilidade = request.form.get("id_disponibilidade")

        if not id_disponibilidade:
            return "Por favor, selecione um horário disponível"

       
        cursor = conexao.cursor(dictionary=True, buffered=True)
        
        cursor.execute("""
            SELECT D.capacidade_maxima, COUNT(P.id_pedido) as total_agendados
            FROM disponibilidade D
            LEFT JOIN pedido P ON D.id_disponibilidade = P.id_disponibilidade
            WHERE D.id_disponibilidade = %s
            GROUP BY D.id_disponibilidade, D.capacidade_maxima
        """, (id_disponibilidade,))

        vaga_info = cursor.fetchone()

        if vaga_info:
            capacidade = vaga_info['capacidade_maxima'] if vaga_info['capacidade_maxima'] is not None else 10
            total_atual = vaga_info['total_agendados'] if vaga_info['total_agendados'] is not None else 0

            if total_atual >= capacidade:
                cursor.close()
                return "Horário indisponível no momento. Por favor, escolha outra disponibilidade."
                

        cursor.close()
        session["id_disponibilidade"] = id_disponibilidade
        return redirect(url_for("publico.resumo_pedido"))
        

    cursor = conexao.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT prazo_minimo_horas FROM configuracao_entrega WHERE id_loja = %s", (id_loja,))
    config = cursor.fetchone()

    prazo_minimo_horas = config["prazo_minimo_horas"] if config and config.get("prazo_minimo_horas") is not None else 24

    agora = datetime.now()
    data_hora_limite = agora + timedelta(hours=prazo_minimo_horas)

    cursor.execute("""
        SELECT D.id_disponibilidade, D.data_disponivel, D.hora_inicio, D.hora_fim, D.capacidade_maxima,
               COUNT(P.id_pedido) as total_agendados
        FROM disponibilidade D
        LEFT JOIN pedido P ON D.id_disponibilidade = P.id_disponibilidade
        WHERE D.id_loja = %s AND D.ativo = 1
        GROUP BY D.id_disponibilidade, D.data_disponivel, D.hora_inicio, D.hora_fim, D.capacidade_maxima
        ORDER BY D.data_disponivel ASC, D.hora_inicio ASC
    """, (id_loja,))

    todos_horarios = cursor.fetchall()
    cursor.close()

    horarios_disponiveis = []

    for h in todos_horarios:
        data_str = str(h['data_disponivel'])
        hora_str = str(h['hora_inicio'])

        data_hora_slot_str = f"{data_str} {hora_str}"

        try:
            data_hora_slot = datetime.strptime(data_hora_slot_str, "%Y-%m-%d %H:%M:%S")

            capacidade = h['capacidade_maxima'] if h['capacidade_maxima'] is not None else 10
            total_agendados = h['total_agendados'] if h['total_agendados'] is not None else 0

            if data_hora_slot >= data_hora_limite and total_agendados < capacidade:
                horarios_disponiveis.append(h)

        except ValueError:
            continue

    print("HORÁRIOS VÁLIDOS APÓS O PRAZO MÍNIMO:", horarios_disponiveis)

    return render_template("publico/agendamento.html", horarios_disponiveis=horarios_disponiveis)

        

@publico_bp.route("/checkout/iniciar", methods=["GET"])
def iniciar_checkout():
    
    if "id_cliente" in session:
        
        return redirect(url_for("publico.escolher_modalidade"))
    else:
        
        return redirect(url_for("cliente.cadastro_cliente"))
    
@publico_bp.route("/resumo-pedido", methods=["GET", "POST"])
def resumo_pedido():
    id_cliente = session.get("id_cliente")
    if not id_cliente:
        return redirect(url_for("cliente.login"))

    carrinho = session.get("carrinho", {})
    if not carrinho:
        return redirect(url_for("publico.cardapio1-publico"))

    numero_pedido = str(int(time.time()))
    id_disponibilidade = session.get("id_disponibilidade")
    id_loja = session.get("id_loja", 13)
    
    id_endereco_escolhido = session.get("id_endereco_entrega")
    endereco_cliente = None

    cursor = conexao.cursor(dictionary=True, buffered=True)

    if id_endereco_escolhido:
        cursor.execute("""
            SELECT * FROM endereco_cliente
            WHERE id_endereco_cliente = %s AND id_cliente = %s
        """, (id_endereco_escolhido, id_cliente))
        endereco_cliente = cursor.fetchone()
    
    if not endereco_cliente:
        cursor.execute("""
            SELECT * FROM endereco_cliente
            WHERE id_cliente = %s
            ORDER BY id_endereco_cliente DESC LIMIT 1
        """, (id_cliente,))
        endereco_cliente = cursor.fetchone()

    cursor.execute("SELECT * FROM endereco_loja WHERE id_loja=%s", (id_loja,))
    endereco_loja = cursor.fetchone()

    horario_escolhido = None
    horario_entrega = None

    if id_disponibilidade:
        cursor.execute("SELECT * FROM disponibilidade WHERE id_disponibilidade = %s", (id_disponibilidade,))
        horario_escolhido = cursor.fetchone()
        
        if horario_escolhido:
            data_disp = horario_escolhido["data_disponivel"]
            hora_disp = horario_escolhido.get("hora_inicio") or horario_escolhido.get("horario")
            horario_entrega = f"{data_disp} {hora_disp}"

    total_produtos = sum(item["preco"] * item["quantidade"] for item in carrinho.values())

    str_end_loja = f"{endereco_loja.get('rua')}, {endereco_loja.get('numero')}, {endereco_loja.get('bairro')}" if endereco_loja else ""
    str_end_cliente = f"{endereco_cliente.get('rua')}, {endereco_cliente.get('numero')}, {endereco_cliente.get('bairro')}" if endereco_cliente else ""

    lat_loja, lon_loja = obter_coordenadas(str_end_loja) if str_end_loja else (None, None)
    lat_cliente, lon_cliente = obter_coordenadas(str_end_cliente) if str_end_cliente else (None, None)

    distancia_km = 1.0
    if lat_loja and lon_loja and lat_cliente and lon_cliente:
        distancia_km = calcular_distancia_km(lat_loja, lon_loja, lat_cliente, lon_cliente)

    faixa_calculada = math.ceil(distancia_km)

    cursor.execute("SELECT id_configuracao_entrega FROM configuracao_entrega WHERE id_loja = %s LIMIT 1", (id_loja,))
    config_entrega = cursor.fetchone()
    
    taxa_entrega = 0.0
    if config_entrega:
        id_cfg = config_entrega["id_configuracao_entrega"]
        cursor.execute("""
            SELECT valor_taxa FROM taxa_entrega 
            WHERE id_configuracao_entrega = %s 
            AND distancia_maxima_entrega >= %s 
            ORDER BY distancia_maxima_entrega ASC 
            LIMIT 1
        """, (id_cfg, faixa_calculada))
        
        taxa_obj = cursor.fetchone()
        if taxa_obj:
            taxa_entrega = float(taxa_obj["valor_taxa"])


    modalidade_atual = session.get("modalidade", "entrega")
    if modalidade_atual == "retirada":
        taxa_entrega = 0.0

    total_geral = total_produtos + taxa_entrega
    

    if request.method == "POST":
      
        cursor.execute("SELECT aberta FROM loja WHERE id_loja = %s", (id_loja,))
        loja_status = cursor.fetchone()

        if loja_status and loja_status["aberta"] == 0:
            cursor.close()
            return """
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 9999; font-family: sans-serif;">
                <div style="background: #fff0f5; padding: 30px; border-radius: 16px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.2); max-width: 400px; border: 2px solid #ffb6c1;">
                    <h2 style="color: #d81b60; margin-top: 0;">Loja Fechada! 🧁</h2>
                    <p style="color: #555; font-size: 16px; line-height: 1.5;">Poxa, a loja acabou de fechar e não está aceitando novos pedidos no momento. Volte mais tarde para garantir sua encomenda!</p>
                    <a href="/" style="display: inline-block; margin-top: 15px; background: #e91e63; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; transition: background 0.3s;">Voltar para o Cardápio</a>
                </div>
            </div>
            """


        try:
            if not horario_entrega or not id_disponibilidade:
                return "Erro: Nenhum horário de agendamento válido foi encontrado."

            valor_total = total_produtos + taxa_entrega  

            sql_pedido = """
                INSERT INTO pedido (id_cliente, id_loja, numero_pedido, modalidade, data_pedido, data_agendada, id_disponibilidade, subtotal, taxa_entrega, valor_total, status_pedido) 
                VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_pedido, (
                id_cliente,
                id_loja,
                numero_pedido,
                modalidade_atual,
                horario_entrega,
                id_disponibilidade,
                total_produtos,
                taxa_entrega,
                valor_total,
                'Aguardando Confirmação'
            ))

            id_pedido_gerado = cursor.lastrowid

            if endereco_cliente and modalidade_atual != "retirada":
                sql_end_pedido = """
                    INSERT INTO endereco_pedido (
                        id_pedido, rua, numero, bairro, cep, complemento, referencia
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_end_pedido, (
                    id_pedido_gerado,
                    endereco_cliente["rua"],
                    endereco_cliente["numero"],
                    endereco_cliente["bairro"],
                    endereco_cliente["cep"],
                    endereco_cliente.get("complemento"),
                    endereco_cliente.get("referencia")
                ))

            for id_produto, item in carrinho.items():
                subtotal_item = item["quantidade"] * item["preco"]
                sql_item = """
                    INSERT INTO item_pedido (id_pedido, id_produto, quantidade, preco_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql_item, (
                    id_pedido_gerado,
                    id_produto,
                    item["quantidade"],
                    item["preco"],
                    subtotal_item
                ))

            conexao.commit()

            session.pop("carrinho", None)
            session.pop("id_disponibilidade", None)
            session.pop("id_endereco_entrega", None)

        except Exception as e:
            conexao.rollback()
            print("ERRO AO SALVAR PEDIDO:", e)
            return f"Ocorreu um erro ao registrar o pedido: {e}"

        finally:
            cursor.close()
           
        return render_template("publico/pedido_sucesso.html")

    return render_template(
        "publico/resumo_pedido.html",
        carrinho=carrinho,
        total_produtos=total_produtos,
        taxa_entrega=taxa_entrega,
        total_geral=total_geral,
        endereco=endereco_cliente,
        horario_entrega=horario_entrega,
        horario_escolhido=horario_escolhido,
        numero_pedido=numero_pedido
    )
@publico_bp.route("/salvar-agendamento", methods=["POST"])
def salvar_agendamento():
    horario = request.form.get("horario_entrega")

    session["horario_entrega"] = horario

    return redirect(url_for("publico.resumo_pedido"))

