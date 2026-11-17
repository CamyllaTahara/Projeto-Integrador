from flask import Blueprint, render_template, request, redirect, session, url_for
from database import conexao

cliente_bp=Blueprint("cliente",__name__)

@cliente_bp.route("/cliente/cadastro_cliente", methods=["GET","POST"])
def cadastro_cliente():
    if request.method=="POST":
        
        nome_cliente=request.form["nome_cliente"].strip().title()
        if not nome_cliente:
            return "Nome é obrigatório."

        whatsapp=request.form["whatsapp"]
        if not whatsapp:
         return "WhatsApp é obrigatório."
        
        if len(whatsapp) !=11 or not whatsapp.isdigit():
         return "O número de WhatsApp deve conter 11 números."
        
        telefone_secundario=request.form["telefone_secundario"]
        if telefone_secundario and (len(telefone_secundario) != 11 or not telefone_secundario.isdigit()):
         return "O número de telefone deve conter 11 números."


        

        cursor=conexao.cursor()
        sql="""
        INSERT INTO cliente (
        nome_cliente,
        whatsapp,
        telefone_secundario
      
        )
        VALUES (%s,%s,%s)
        """
        valores=(
            nome_cliente,
            whatsapp,
            telefone_secundario
        )

        cursor.execute(sql, valores)
        conexao.commit()

        id_cliente = cursor.lastrowid
        cursor.close()

        session["id_cliente"] = id_cliente
        session["nome_cliente"] = nome_cliente

        return redirect(url_for("publico.escolher_modalidade"))
    
    return render_template("/cliente/cadastro_cliente.html")


@cliente_bp.route("/cliente/login",methods=["GET","POST"])
def login_cliente():

    if request.method=="POST":

        whatsapp=request.form["whatsapp"].strip().lower()

        cursor = conexao.cursor()

        sql="""

        SELECT id_cliente, nome_cliente
        FROM cliente
        WHERE whatsapp = %s
        """

        cursor.execute(sql,(whatsapp,))
        cliente=cursor.fetchone()
        cursor.close()

        if not cliente:
         print("WHATSAPP NÃO ENCONTRADO")
         return "Número de WhatsApp não cadastrado ou não encontrado."

        print("Cliente",cliente)

        

        session["id_cliente"]=cliente[0]
        session["nome_cliente"]=cliente[1]
        session["whatsapp"]=whatsapp[2]

        carrinho = session.get("carrinho",{})

        if carrinho:
           return redirect(url_for("publico.iniciar_checkout"))
        else:
           return redirect(url_for("cliente.painel_cliente"))
        
    return render_template("cliente/login.html") 

@cliente_bp.route("/cliente/cadastro/sucesso")
def cadastro_sucesso():
   return render_template("/cliente/cadastro_sucesso_cliente.html")


@cliente_bp.route("/cliente/painel-cliente")

def painel_cliente():

   id_cliente = session.get("id_cliente")

   if not id_cliente:
    return redirect(url_for("cliente.login"))

   cursor = conexao.cursor(dictionary=True, buffered=True)
   
   cursor.execute("""
   SELECT * FROM cliente WHERE id_cliente = %s
   """,(id_cliente,))

   cliente_info = cursor.fetchone()

   cursor.execute("""
   SELECT p.*, ep.rua, ep.numero, ep.bairro, l.nome_loja
   FROM pedido p
   LEFT JOIN endereco_pedido ep ON p.id_pedido = ep.id_pedido
   LEFT JOIN loja l ON p.id_loja = l.id_loja
   WHERE p.id_cliente = %s
   ORDER BY p.data_pedido DESC
   """,(id_cliente,))

   pedidos = cursor.fetchall()

   for pedido in pedidos:
        cursor.execute("""
            SELECT ip.*, pr.nome_produto 
            FROM item_pedido ip
            LEFT JOIN produto pr ON ip.id_produto = pr.id_produto
            WHERE ip.id_pedido = %s
        """, (pedido["id_pedido"],))
        pedido["itens"] = cursor.fetchall()

   cursor.close()

   pedidos_andamento = [p for p in pedidos if p["status_pedido"] !="Concluido" and p["status_pedido"] !="Cancelado"]
   historico_pedidos = [p for p in pedidos if p["status_pedido"] !="Concluido" and p["status_pedido"] !="Cancelado"]

   return render_template(
      "cliente/painel_cliente.html",
      cliente = cliente_info,
      pedidos_andamento = pedidos_andamento,
      historico_pedidos = historico_pedidos
   )

@cliente_bp.route("/cliente/painel-cliente/editar",methods=["POST"])
def editar_cliente():
   id_cliente = session.get("id_cliente")
   if not id_cliente:
      return redirect(url_for("cliente.login_cliente"))

   novo_nome  = request.form.get("nome_cliente","").strip()
   novo_whatsapp = request.form.get("whatsapp","").strip()

   if novo_nome or novo_whatsapp:
      cursor = conexao.cursor(dictionary=True, buffered=True)
      cursor.execute("""
      UPDATE cliente
      SET nome_cliente = %s, whatsapp = %s
      WHERE id_cliente = %s
      """, (novo_nome, novo_whatsapp, id_cliente))
      conexao.commit()
      cursor.close()

   return redirect(url_for("cliente.painel_cliente"))




@cliente_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('cliente.login_cliente')) 