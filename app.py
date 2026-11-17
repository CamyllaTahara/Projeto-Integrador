from flask import Flask, render_template, request
from werkzeug.security import generate_password_hash
from database import conexao
from routes.loja import loja_bp
from routes.cliente import cliente_bp
from routes.publico import publico_bp

app = Flask(__name__)
app.secret_key = "2701"
app.register_blueprint(loja_bp)
app.register_blueprint(cliente_bp)
app.register_blueprint(publico_bp)

@app.route("/")
def inicio():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)