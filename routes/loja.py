from sqlite3 import Cursor
import uuid
import math
from flask import Blueprint, render_template, request, redirect, session, url_for
import urllib
from werkzeug.security import generate_password_hash, check_password_hash
from database import conexao
import os
from werkzeug.utils import secure_filename
import pywhatkit as kit
from flask import render_template, request, redirect, url_for, session

loja_bp=Blueprint("loja", __name__)

@loja_bp.route("/loja/cadastro", methods=["GET","POST"])
def cadastro_loja():
    if request.method=="POST":

        nome_responsavel=request.form["nome_responsavel"].strip().title()
        if not nome_responsavel:
            return "Nome do responsável é obrigatório."


        nome_loja=request.form["nome_loja"].strip().title()
        if not nome_loja:
            return "Nome da loja é obrigatório."

        cnpj=request.form["cnpj"]
        if not cnpj:
            return "CNPJ é obrigatório."

        if len(cnpj) !=14 or not cnpj.isdigit():
            return "O CNPJ deve ter 14 números."

        whatsapp=request.form["whatsapp"]
        if not whatsapp:
            return "WhatsApp é obrigatório."

        if len(whatsapp) !=11 or not whatsapp.isdigit():
            return "O número de WhatsApp deve conter 11 números."

        email=request.form["email"].strip().lower()
        if not email:
            return "E-mail é obrigatório."

        if "@" not in email or "." not in email:
            return "Digite um e-mail válido."
        
        senha=request.form["senha"]
        if not senha:
           return "Por favor, crie uma senha."
        if len(senha)<8:
            return "A senha deve conter pelo menos 8 caracteres."
        if not any(caracter.isdigit() for caracter in senha):
            return "A senha deve conter pelo menos um número."

        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        whatsapp_limpo = whatsapp.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

        senha_hash=generate_password_hash(senha)
        print(senha_hash)
        print("Senha digitada no cadastro:", repr(senha))
        print("Hash gerado:", senha_hash)
        print("Teste do hash:", check_password_hash(senha_hash, senha))

        logo=request.files["logo"]

        if logo:
            caminho_logo = os.path.join("static","img","logos",logo.filename)
            logo.save(caminho_logo)
            print("Caminho logo:",logo)

        cursor=conexao.cursor()
        sql="""
        INSERT INTO loja (
        nome_responsavel,
        nome_loja,
        cnpj,
        whatsapp,
        email,
        senha,
        logo
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        valores=(
            nome_responsavel,
            nome_loja,
            cnpj_limpo,
            whatsapp_limpo,
            email,
            senha_hash,
            caminho_logo
        )

        cursor.execute(sql, valores)
        conexao.commit()

        return redirect("/loja/cadastro/sucesso")


    return render_template("loja/cadastro.html")

@loja_bp.route("/loja/cadastro/sucesso")
def cadastro_sucesso():
    return render_template("/loja/cadastro_sucesso.html")

@loja_bp.route("/loja/login",methods=["GET","POST"])
def login_loja():

    if request.method=="POST":

        email=request.form["email"].strip().lower()
        senha=request.form["senha"]

        cursor = conexao.cursor()

        sql="""

        SELECT id_loja, nome_loja, senha
        FROM loja
        WHERE email = %s
        """

        cursor.execute(sql,(email,))
        loja=cursor.fetchone()
        cursor.close()

        if not loja:
         print("E-MAIL NÃO ENCONTRADO")
         return "E-mail ou senha inválidos."

        print("loja encontrada",loja)

        if not check_password_hash(loja[2],senha):
         print("SENHA NÃO ENCONTRADA")
         return "E-mail ou senha inválidos."
        

        session["id_loja"]=loja[0]
        session["nome_loja"]=loja[1]
        session["senha"]=loja[2]
        

        return redirect(url_for("loja.painel_loja"))

    return render_template("loja/login.html") 

@loja_bp.route("/loja/painel")
def painel_loja():

    if "id_loja" not in session:
        return redirect("/loja/login")

    return render_template("loja/painel.html")

@loja_bp.route("/loja/logout")
def logout_loja():
    session.clear()

    return redirect (url_for("loja.login_loja"))


@loja_bp.route("/loja/produtos", methods=["GET","POST"])
def produtos():

    if "id_loja" not in session:
        return redirect(url_for("loja.login_loja"))

    id_loja=session["id_loja"]


    if request.method == "POST":

        nome_produto=request.form["nome_produto"]
        descricao=request.form["descricao"]
        peso_gramas=request.form["peso_gramas"]
        quantidade_porcoes=request.form["quantidade_porcoes"]
        preco=request.form["preco"]
        estoque=request.form["estoque"]
        foto_produto = request.files.get("foto_produto")
        video_produto = request.files.get("video_produto")

        cursor = conexao.cursor()
        sql_produto = """
        INSERT INTO produto (
        id_loja, nome_produto, descricao, peso_gramas, quantidade_porcoes,
        preco, estoque)
        VALUES (%s,%s,%s,%s,%s,%s,%s)"""

        valores = (
                id_loja,
                nome_produto,
                descricao,
                peso_gramas,
                quantidade_porcoes,
                preco,
                estoque
            )
        cursor.execute(sql_produto, valores)
        id_produto =  cursor.lastrowid

        if foto_produto and foto_produto.filename:
            extensao = os.path.splitext(foto_produto.filename)[1]
            nome_limpo = secure_filename(os.path.splitext(foto_produto.filename)[0])
            nome_foto_unica = f"{uuid.uuid4().hex[:8]}_{nome_limpo}{extensao}"

            caminho_disco = os.path.join("static", "img", "produto", nome_foto_unica)
            foto_produto.save(caminho_disco)

            caminho_banco_foto = f"img/produto/{nome_foto_unica}"

            sql_foto = """
            INSERT INTO foto_produto (id_produto, caminho_foto)
            VALUES (%s, %s)"""

            cursor.execute(sql_foto, (id_produto, caminho_banco_foto))

        if video_produto and video_produto.filename !='':
            extensao_v = os.path.splitext(video_produto.filename)[1]
            nome_limpo_v = secure_filename(os.path.splitext(video_produto.filename)[0])
            nome_video_unico = f"{uuid.uuid4().hex[:8]}_{nome_limpo_v}{extensao_v}"

            caminho_disco_v = os.path.join("static", "video", "produto", nome_video_unico)
            video_produto.save(caminho_disco_v)

            caminho_banco_video = f"video/produto/{nome_video_unico}"

            sql_video = """
            INSERT INTO video_produto (id_produto, caminho_video)
            VALUES (%s, %s)"""

            cursor.execute(sql_video, (id_produto, caminho_banco_video))

        conexao.commit()
        cursor.close()

    cursor = conexao.cursor(dictionary=True)

    sql="""
    SELECT 
            p.id_produto,
            p.nome_produto,
            p.descricao,
            p.peso_gramas,
            p.quantidade_porcoes,
            p.preco,
            p.estoque,
            p.ativo,
            fp.caminho_foto,
            vp.caminho_video
        FROM produto p
        LEFT JOIN foto_produto fp ON p.id_produto = fp.id_produto
        LEFT JOIN video_produto vp ON p.id_produto = vp.id_produto
        WHERE p.id_loja = %s
"""
    cursor.execute(sql,(id_loja,))
    produtos = cursor.fetchall()
    cursor.close()

    return render_template("loja/produtos.html", produtos=produtos)



@loja_bp.route("/loja/produtos/editar/<int:id_produto>", methods=["GET", "POST"])
def editar_produto(id_produto):

    if "id_loja" not in session:
        return redirect(url_for("loja.login_loja"))

    id_loja = session["id_loja"]

    if request.method == "POST":

        nome_produto = request.form["nome_produto"]
        descricao = request.form["descricao"]
        peso_gramas = request.form["peso_gramas"]
        quantidade_porcoes = request.form["quantidade_porcoes"]
        preco = request.form["preco"]
        estoque = request.form["estoque"]
        foto = request.files.get("foto_produto")
        video = request.files.get("video_produto")

        cursor = conexao.cursor()

        sql = """
        UPDATE produto SET
            nome_produto = %s,
            descricao = %s,
            peso_gramas = %s,
            quantidade_porcoes = %s,
            preco = %s,
            estoque = %s
        WHERE id_produto = %s
        AND id_loja = %s
        """

        valores = (
            nome_produto,
            descricao,
            peso_gramas,
            quantidade_porcoes,
            preco,
            estoque,
            id_produto,
            id_loja
        )

        cursor.execute(sql, valores)

        
        if foto and foto.filename:

            extensao = os.path.splitext(foto.filename)[1]
            nome_limpo = secure_filename(os.path.splitext(foto.filename)[0])
            nome_foto_unica = f"{uuid.uuid4().hex[:8]}_{nome_limpo}{extensao}"

            caminho_disco = os.path.join("static", "img", "produto", nome_foto_unica)
            foto.save(caminho_disco)

            caminho_banco = f"img/produto/{nome_foto_unica}"

            sql_antiga = """
            SELECT id_foto, caminho_foto
            FROM foto_produto
            WHERE id_produto = %s
            """

            cursor.execute(sql_antiga, (id_produto,))
            foto_antiga = cursor.fetchone()

            if foto_antiga:
                sql_update = """
                UPDATE foto_produto
                SET caminho_foto = %s
                WHERE id_foto = %s
                """
                cursor.execute(sql_update, (caminho_banco, foto_antiga[0]))

                caminho_arquivo_antigo = os.path.join("static", foto_antiga[1])
                if os.path.exists(caminho_arquivo_antigo):
                    os.remove(caminho_arquivo_antigo)

            else: 
                sql_insert = """
                INSERT INTO foto_produto (id_produto, caminho_foto)
                VALUES (%s, %s)
                """
                cursor.execute(sql_insert, (id_produto, caminho_banco))




        if video and video.filename:
            extensao_v = os.path.splitext(video.filename)[1]
            nome_v_limpo = secure_filename(os.path.splitext(video.filename)[0])
            nome_video_unico = f"{uuid.uuid4().hex[:8]}_{nome_v_limpo}{extensao_v}"

            caminho_disco_v = os.path.join("static","video","produto", nome_video_unico)
            video.save(caminho_disco_v)
            caminho_banco_v = f"video/produto/{nome_video_unico}"

            sql_video_antigo = """ SELECT id_video_produto, caminho_video
            FROM video_produto
            WHERE id_produto = %s"""

            cursor.execute(sql_video_antigo,(id_produto,))
            video_antigo = cursor.fetchone()

            if video_antigo:
                sql_update_v=""" UPDATE video_produto
                SET caminho_video = %s
                WHERE id_video_produto = %s"""

                cursor.execute(sql_update_v,(caminho_banco_v,video_antigo[0]))

                caminho_arquivo_antigo_v = os.path.join("static",video_antigo[1])
                if os.path.exists(caminho_arquivo_antigo_v):
                    os.remove(caminho_arquivo_antigo_v)

            else:
                sql_insert_v = """ INSERT INTO video_produto (id_produto, caminho_video)
                VALUES (%s, %s)"""

                cursor.execute(sql_insert_v,(id_produto,caminho_banco_v))



        conexao.commit()
        cursor.close()

        return redirect(url_for("loja.editar_produto", id_produto=id_produto))


    cursor = conexao.cursor(dictionary=True)

    sql_produto = """
    SELECT id_produto, 
           nome_produto, 
           descricao, 
           peso_gramas,
           quantidade_porcoes,
           preco,
           estoque,
           ativo
    FROM produto
    WHERE id_produto = %s
    AND id_loja = %s
    """

    cursor.execute(sql_produto, (id_produto, id_loja))
    produto = cursor.fetchone()


    cursor = conexao.cursor(dictionary=True)
    sql_fotos = "SELECT * FROM foto_produto WHERE id_produto = %s"
    cursor.execute(sql_fotos, (id_produto,))
    fotos = cursor.fetchall()

    sql_video = "SELECT * FROM video_produto WHERE id_produto = %s"
    cursor.execute(sql_video,(id_produto,))
    video_produto = cursor.fetchone()

    cursor.close()

    if not produto:
        return "Produto não encontrado"


    return render_template("loja/editar_produto.html", produto=produto, fotos=fotos, video_produto = video_produto)


@loja_bp.route("/loja/perfil/editar/<int:id_loja>", methods=["GET", "POST"])
def editar_perfil(id_loja):

    if "id_loja" not in session:
        return redirect(url_for("loja.login_loja"))

    id_loja = session["id_loja"]

    if request.method == "POST":
        nome_responsavel = request.form.get("nome_responsavel", "")
        nome_loja = request.form.get("nome_loja", "")
        whatsapp = request.form.get("whatsapp", "")
        email = request.form.get("email", "")
        cnpj = request.form.get("cnpj", "")

        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        whatsapp_limpo = whatsapp.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

        logo = request.files.get("logo")

        cursor = conexao.cursor()

        if logo and logo.filename != "":
            extensao = os.path.splitext(logo.filename)[1]
            nome_limpo = secure_filename(os.path.splitext(logo.filename)[0])
            nome_foto_unica = f"{uuid.uuid4().hex[:8]}_{nome_limpo}{extensao}"
            caminho_logo = os.path.join("static","img", "logos", logo.filename)
            logo.save(caminho_logo)
            caminho_banco = f"img/logos/{logo.filename}"

            sql = """ 
            UPDATE loja SET
                nome_responsavel = %s,
                nome_loja = %s,
                whatsapp = %s,
                email = %s,
                cnpj = %s,
                logo = %s
            WHERE id_loja = %s
            """
            valores = (
                nome_responsavel,
                nome_loja,
                whatsapp_limpo,
                email,
                cnpj_limpo,
                caminho_banco,
                id_loja
            )
        else:
            sql = """
            UPDATE loja SET
                nome_responsavel = %s,
                nome_loja = %s,
                whatsapp = %s,
                email = %s,
                cnpj = %s
            WHERE id_loja = %s
            """
            valores = (
                nome_responsavel,
                nome_loja,
                whatsapp_limpo,
                email,
                cnpj_limpo,
                id_loja
            )

        cursor.execute(sql, valores,caminho_banco)
        conexao.commit()
        cursor.close()

        return redirect(url_for("loja.editar_perfil", id_loja=id_loja))

    cursor = conexao.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM loja where id_loja = %s", (id_loja,))
    loja = cursor.fetchone()
    cursor.close()

    if not loja:
        return "Loja não encontrada"

    return render_template("loja/editar_perfil.html", loja=loja)





@loja_bp.route("/loja/produtos/excluir/<int:id_produto>", methods=["GET","POST"])
def excluir_produto(id_produto):

    if "id_loja" not in session:
        return redirect(url_for("loja.login_loja"))

    id_loja=session["id_loja"]

    cursor = conexao.cursor()

    
    cursor.execute("DELETE FROM foto_produto WHERE id_produto=%s",(id_produto,))

    cursor.execute("DELETE FROM video_produto WHERE id_produto=%s",(id_produto,))

    cursor.execute("DELETE FROM produto WHERE id_produto=%s AND id_loja=%s", (id_produto, id_loja))


    conexao.commit()                                                                                                

    return redirect(url_for("loja.produtos"))


@loja_bp.route("/loja/produtos/status/<int:id_produto>", methods=["GET","POST"])
def status_produto(id_produto):

    if "id_loja" not in session:
        return redirect (url_for("loja.login_loja"))

    id_loja = session["id_loja"]
    cursor =  conexao.cursor(dictionary=True)

    

    cursor.execute("SELECT ativo FROM produto WHERE id_produto = %s AND id_loja=%s",(id_produto, id_loja))
    
    produto = cursor.fetchone()

    if produto:

        novo_status = 0 if produto["ativo"] == 1 else 1

        cursor.execute("UPDATE produto SET ativo = %s WHERE id_produto =%s AND id_loja =%s",(novo_status, id_produto, id_loja))

        conexao.commit()

    cursor.close()
    return redirect(url_for("loja.produtos"))

@loja_bp.route("/configurar-entrega", methods=["GET","POST"])
def configurar_entrega():
    id_loja = session.get("id_loja")

    cursor = conexao.cursor(dictionary=True, buffered=True)

    if request.method=="POST":

        cep= request.form.get("cep")
        rua = request.form.get("rua")
        numero=request.form.get("numero")
        bairro=request.form.get("bairro")

        raio_maximo_km = request.form.get("raio_maximo_km")
        permite_entrega = 1 if request.form.get("permite_entrega") else 0
        permite_retirada = 1 if request.form.get("permite_retirada") else 0


        cursor.execute("SELECT id_endereco_loja FROM endereco_loja WHERE id_loja = %s",(id_loja,))
        end_atual = cursor.fetchone()

        if end_atual:
            
            print("VALORES RECEBIDOS:", id_loja, permite_entrega, permite_retirada, raio_maximo_km)
            sql_end = "UPDATE endereco_loja SET cep=%s, rua=%s, numero=%s,bairro=%s WHERE id_loja=%s" 
            cursor.execute(sql_end,(cep, rua, numero, bairro, id_loja))

        else:
            sql_end = "INSERT INTO endereco_loja (id_loja, cep, rua, numero, bairro) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql_end,(id_loja, cep, rua, numero, bairro))


        sql_cfg="""
        INSERT INTO configuracao_entrega (id_loja, permite_entrega, permite_retirada, raio_maximo_km) VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
        permite_entrega=VALUES(permite_entrega),
        permite_retirada=VALUES(permite_retirada),
        raio_maximo_km=VALUES(raio_maximo_km)
        """
        cursor.execute(sql_cfg,(id_loja, permite_entrega,permite_retirada,raio_maximo_km))

        conexao.commit()
        cursor.close()
        return redirect(url_for("loja.configurar_entrega"))

    cursor.execute("SELECT * FROM endereco_loja WHERE id_loja = %s",(id_loja,))
    endereco = cursor.fetchone()

    cursor.execute("SELECT * FROM configuracao_entrega WHERE id_loja=%s",(id_loja,))
    config=cursor.fetchone()
    faixas_km = []

    if config and config.get("raio_maximo_km"):
        id_cfg = config['id_configuracao_entrega']
        raio_max = int(float(config['raio_maximo_km']))

        cursor.execute("SELECT * FROM taxa_entrega WHERE id_configuracao_entrega=%s",(id_cfg,))
        taxas_existentes = cursor.fetchall()

        mapa_taxas = {int(float(t['distancia_maxima_entrega'])): t['valor_taxa'] for t in taxas_existentes}

        for km in range(1, raio_max +1):
            faixas_km.append({
                "km":km,
                "valor": mapa_taxas.get(km, 0.00)
            })

    cursor.close()
    return render_template("loja/configurar_entrega.html",endereco=endereco, config=config, faixas_km=faixas_km)
        


@loja_bp.route("/salvar-taxas-km", methods=["POST"])
def salvar_taxas_km():
    id_loja=session.get("id_loja")
    cursor=conexao.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT id_configuracao_entrega FROM configuracao_entrega WHERE id_loja=%s",(id_loja,))
    cfg=cursor.fetchone()

    if cfg:
        id_config = cfg['id_configuracao_entrega']

        kms = request.form.getlist("distancia_km")
        valores = request.form.getlist("valor_taxa")

        sql = """
        INSERT INTO taxa_entrega (id_configuracao_entrega, distancia_maxima_entrega,valor_taxa) VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE valor_taxa = VALUES(valor_taxa)"""

        for km, valor in zip(kms, valores):
            if valor !="":
                cursor.execute(sql,(id_config,km,valor))

        conexao.commit()
    cursor.close()
    return redirect(url_for("loja.configurar_entrega"))


@loja_bp.route("/cadastrar-disponibilidade", methods=["GET","POST"])
def cadastrar_disponibilidade():
    id_loja=session.get("id_loja",13)

    if request.method == "POST":
        data_disponivel = request.form.get("data_disponivel")
        hora_inicio = request.form.get("hora_inicio")
        hora_fim = request.form.get("hora_fim")
        capacidade_maxima = request.form.get("capacidade_maxima")


        cursor = conexao.cursor(dictionary=True, buffered=True)

        try:
            sql="""
            INSERT INTO disponibilidade (id_loja, data_disponivel, hora_inicio, hora_fim, capacidade_maxima, ativo) 
            VALUES (%s, %s, %s, %s, %s, 1)"""

            cursor.execute(sql,(id_loja,data_disponivel,hora_inicio,hora_fim,capacidade_maxima))
            conexao.commit()

            return redirect(url_for("loja.cadastrar_disponibilidade"))


        except Exception as e:
            conexao.rollback()
            return f"Erro ao cadastrar: {e}"

        finally:
            cursor.close()

    cursor = conexao.cursor(dictionary=True, buffered=True)

    cursor.execute("""
    SELECT * FROM disponibilidade
    WHERE id_loja=%s
    ORDER BY data_disponivel DESC, hora_inicio, hora_fim ASC
    """, (id_loja,))
    disponibilidade = cursor.fetchall()
    print("DADOS VINDO DO BANCO:", disponibilidade)

    cursor.close()

    return render_template("loja/cadastrar_disponibilidade.html", disponibilidade=disponibilidade)

@loja_bp.route("/painel-pedidos")
def painel_pedidos():

    id_loja = session.get("id_loja",)

    cursor = conexao.cursor(dictionary=True, buffered=True)

    sql_pedidos= """
SELECT
    p.*,
    c.nome_cliente AS nome_cliente,
    TIME_FORMAT(d.hora_inicio, '%H:%i') AS hora_inicio,
    TIME_FORMAT(d.hora_fim, '%H:%i') AS hora_fim
FROM pedido p
JOIN cliente c ON p.id_cliente = c.id_cliente
LEFT JOIN disponibilidade d
    ON p.id_disponibilidade = d.id_disponibilidade
WHERE p.id_loja = %s
AND (
    p.status_pedido != 'Concluido'
    OR (
        p.status_pedido = 'Concluido'
        AND DATE(p.data_pedido) = CURDATE()
    )
)
ORDER BY p.data_pedido DESC
"""
    cursor.execute(sql_pedidos,(id_loja,))
    pedidos = cursor.fetchall()

    print("ID DA LOJA:", id_loja)
    print("QUANTIDADE DE PEDIDOS:", len(pedidos))

    print("PRIMEIRO PEDIDO:")
    print(pedidos[0] if pedidos else "Nenhum pedido encontrado")

    for pedido in pedidos:
        print(repr(pedido.get("status_pedido")))
        cursor.execute("""
        SELECT i.*, p.nome_produto
        FROM item_pedido i
        JOIN produto p ON i.id_produto=p.id_produto
        WHERE i.id_pedido=%s
        """,(pedido["id_pedido"],))
        pedido["itens"]=cursor.fetchall()

        cursor.execute("""
        SELECT * FROM endereco_pedido
        WHERE id_pedido = %s
        """,(pedido["id_pedido"],))

        pedido["endereco"] = cursor.fetchone()

    cursor.close()
    return render_template("loja/painel_pedidos.html",pedidos=pedidos)


@loja_bp.route("/painel/pedido/atualizar/<int:id_pedido>", methods=["POST"])
def atualizar_status_pedido(id_pedido):
    print("CONTEÚDO DA SESSÃO ATUAL:", session)

    if "id_loja" not in session:
        print("Sessão vazia! Redirecionando para login...")
        return redirect(url_for("loja.login_loja"))

    novo_status = request.form.get("status_pedido")

    cursor = conexao.cursor(dictionary=True, buffered=True)

    sql_update = """
    UPDATE pedido SET status_pedido = %s WHERE id_pedido = %s
    """
    cursor.execute(sql_update,(novo_status,id_pedido))
    conexao.commit()

    sql_cliente = """
    SELECT p.id_pedido, c.whatsapp, c.nome_cliente, p.status_pedido
    FROM pedido p
    JOIN cliente c ON p.id_cliente = c.id_cliente
    WHERE p.id_pedido = %s"""

    cursor.execute(sql_cliente,(id_pedido,))
    pedido = cursor.fetchone()
    cursor.close()

    whatsapp = pedido['whatsapp'].replace("(","").replace(")","").replace(" ", "").replace("-", "")
    telefone_completo = "+55" + whatsapp 

    if novo_status == "Aguardando Confirmação":
        mensagem = f"Olá {pedido['nome_cliente']}, recebemos o seu pedido #{pedido['id_pedido']}! Por favor, nos encaminhe o comprovante de pagamento para iniciarmos a produção."
    elif novo_status == "Confirmado":
        mensagem = f"Olá {pedido['nome_cliente']}, boas notícias! O seu pedido #{pedido['id_pedido']} foi confirmado e em breve iniciaremos a produção."
    elif novo_status == "Em preparo":
        mensagem = f"Olá {pedido['nome_cliente']}, o seu pedido #{pedido['id_pedido']} está sendo preparado com muito carinho para você."
    elif novo_status == "Saiu para entrega":
        mensagem = f"Olá {pedido['nome_cliente']}, o seu pedido #{pedido['id_pedido']} está indo até você. Fique atento e aguarde o motoboy chegar até o seu endereço! "
    elif novo_status == "Aguardando retirada":
        mensagem = f"Olá {pedido['nome_cliente']}, o seu pedido #{pedido['id_pedido']} está prontinho. Estamos te aguardando aqui na loja para retirá-lo. Lembre-se, seu pedido ficará disponível para retirada até o horário de fechamento da loja, após este prazo, a retirada fica disponível apenas no dia seguinte."
    elif novo_status == "Concluído":
        mensagem = f"Olá {pedido['nome_cliente']}, o seu pedido #{pedido['id_pedido']} foi entregue/concluído. Agradecemos muito pela preferência e esperamos te ver em breve!"
    else:
        mensagem = f"Olá {pedido['nome_cliente']}, o status do seu pedido #{pedido['id_pedido']} foi atualizado para: *{novo_status}*. Mais informações, trate diretamente com a loja."

    whatsapp_url = f"https://wa.me/{whatsapp}?text={urllib.parse.quote(mensagem)}"

  
    return redirect(whatsapp_url)


@loja_bp.route("/painel/pedido/imprimir/<int:id_pedido>")
def imprimir_pedido(id_pedido):

    if "id_loja" not in session:
        return redirect(url_for("loja.login_loja"))

    cursor = conexao.cursor(dictionary=True, buffered=True)

    cursor.execute("""
   SELECT p.*, c.nome_cliente AS nome_cliente, c.whatsapp, 
               e.rua, e.numero, e.bairro, e.cep, e.complemento, e.referencia,
               d.data_disponivel, d.hora_inicio, d.hora_fim
        FROM pedido p
        JOIN cliente c ON p.id_cliente = c.id_cliente
        LEFT JOIN endereco_pedido e ON p.id_pedido = e.id_pedido
        LEFT JOIN disponibilidade d ON p.id_disponibilidade = d.id_disponibilidade
        WHERE p.id_pedido = %s
    """,(id_pedido,))
    pedido = cursor.fetchone()

    cursor.execute("""
    SELECT ip.*, pr.nome_produto
    FROM item_pedido ip
    JOIN produto pr ON ip.id_produto = pr.id_produto
    WHERE ip.id_pedido = %s
    """,(id_pedido,))

    itens = cursor.fetchall()
    cursor.close()

    return render_template("loja/imprimir_pedido.html", pedido=pedido, itens=itens)
  

@loja_bp.route('/portal_lojas')
def portal_lojas():
    return render_template('loja/portal_loja.html')