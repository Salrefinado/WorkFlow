import os
import zipfile
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

# --- Configuração ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///workflow.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

# --- Modelos do Banco de Dados ---

class Grupo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    ordem = db.Column(db.Integer, default=1)
    orcamentos = db.relationship('Orcamento', backref='grupo', lazy=True)

class Orcamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    cliente = db.Column(db.String(200), nullable=False)
    status_geral = db.Column(db.String(50), default='Novo')
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    
    # Colunas de Etapas (para grupos de Entrada, Visitas, Standby)
    etapa1_descricao = db.Column(db.String(500))
    etapa1_status = db.Column(db.String(50), default='Aguardando') # Tirar Medida / Em Produção / Instalar / Instalado
    
    etapa2_descricao = db.Column(db.String(500))
    etapa2_status = db.Column(db.String(50), default='Aguardando') # Tirar Medida / Em Produção / Instalar / Instalado
    
    # Relações
    tarefas = db.relationship('TarefaProducao', backref='orcamento', lazy=True, cascade="all, delete-orphan")
    arquivos = db.relationship('ArquivoAnexado', backref='orcamento', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "cliente": self.cliente,
            "status_geral": self.status_geral,
            "grupo_id": self.grupo_id,
            "grupo_nome": self.grupo.nome,
            "etapa1_descricao": self.etapa1_descricao,
            "etapa1_status": self.etapa1_status,
            "etapa2_descricao": self.etapa2_descricao,
            "etapa2_status": self.etapa2_status,
            "tarefas": [t.to_dict() for t in self.tarefas],
            "arquivos": [a.to_dict() for a in self.arquivos]
        }

class TarefaProducao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    colaborador = db.Column(db.String(100), nullable=False) # Edison, Luiz, etc.
    item_descricao = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Não Iniciado') # Não Iniciado / Iniciou a Produção / Fase de Acabamento / Produção Finalizada
    
    def to_dict(self):
        return {
            "id": self.id,
            "colaborador": self.colaborador,
            "item_descricao": self.item_descricao,
            "status": self.status
        }

class ArquivoAnexado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    nome_arquivo = db.Column(db.String(300))
    caminho_arquivo = db.Column(db.String(500)) # Caminho relativo (ex: 'uploads/orcamento_cliente_123.pdf')

    def to_dict(self):
        return {
            "id": self.id,
            "nome_arquivo": self.nome_arquivo,
            "url": f"/{self.caminho_arquivo}"
        }

# --- Rota Principal (Frontend) ---

@app.route('/')
def index():
    return render_template('index.html')

# --- Rotas da API ---

@app.route('/api/workflow', methods=['GET'])
def get_workflow():
    grupos = Grupo.query.order_by(Grupo.ordem).all()
    workflow_data = []
    for grupo in grupos:
        orcamentos_data = [o.to_dict() for o in grupo.orcamentos]
        workflow_data.append({
            "id": grupo.id,
            "nome": grupo.nome,
            "orcamentos": orcamentos_data
        })
    return jsonify(workflow_data)

@app.route('/api/upload', methods=['POST'])
def upload_orcamento():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({"error": "Arquivo inválido, envie um .zip"}), 400

    json_data = None
    pdf_files = []

    try:
        with zipfile.ZipFile(file, 'r') as zf:
            for filename in zf.namelist():
                if filename.endswith('.json'):
                    with zf.open(filename) as f:
                        json_data = json.load(f)
                elif filename.endswith('.pdf'):
                    # Extrai e salva o PDF
                    safe_filename = secure_filename(os.path.basename(filename))
                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                    with open(target_path, 'wb') as f:
                        f.write(zf.read(filename))
                    pdf_files.append({"nome": safe_filename, "caminho": f"uploads/{safe_filename}"})

        if not json_data:
            return jsonify({"error": "Arquivo .json não encontrado no .zip"}), 400

        # Cria o orçamento no grupo "Entrada de Orçamentos" (ID 1)
        novo_orcamento = Orcamento(
            numero=json_data.get('numero_orcamento', 'N/A'),
            cliente=json_data.get('nome_cliente', 'N/A'),
            grupo_id=1, # ID 1 = "Entrada de Orçamentos"
            etapa1_descricao=json_data.get('itens_etapa_1', ''),
            etapa2_descricao=json_data.get('itens_etapa_2', '')
        )
        db.session.add(novo_orcamento)
        db.session.commit() # Commit para obter o ID do novo_orcamento
        
        # Adiciona os arquivos PDF extraídos ao banco de dados
        for pdf in pdf_files:
            anexo = ArquivoAnexado(
                orcamento_id=novo_orcamento.id,
                nome_arquivo=pdf['nome'],
                caminho_arquivo=pdf['caminho']
            )
            db.session.add(anexo)

        # Cria as tarefas de produção
        colaboradores_fixos = ["Edison", "Luiz", "Hélio", "José", "Anderson", "Eudes", "Pintura"]
        if 'tarefas_producao' in json_data:
            for tarefa_info in json_data['tarefas_producao']:
                if tarefa_info.get('colaborador') in colaboradores_fixos:
                    tarefa = TarefaProducao(
                        orcamento_id=novo_orcamento.id,
                        colaborador=tarefa_info['colaborador'],
                        item_descricao=tarefa_info.get('item', 'Item não descrito')
                    )
                    db.session.add(tarefa)
        
        db.session.commit()

        return jsonify(novo_orcamento.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/orcamento/<int:orc_id>/add_file', methods=['POST'])
def add_file_to_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo inválido"}), 400
        
    try:
        safe_filename = secure_filename(file.filename)
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(target_path)
        
        anexo = ArquivoAnexado(
            orcamento_id=orcamento.id,
            nome_arquivo=safe_filename,
            caminho_arquivo=f"uploads/{safe_filename}"
        )
        db.session.add(anexo)
        db.session.commit()
        
        return jsonify(anexo.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    # O path agora pode ser 'uploads/arquivo.pdf', então usamos a pasta base
    base_dir = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(base_dir, file_name)


@app.route('/api/orcamento/<int:orc_id>/etapa', methods=['PUT'])
def update_etapa_status(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: return jsonify({"error": "Orçamento não encontrado"}), 404
        
    data = request.json
    etapa = data.get('etapa') # 'etapa1' ou 'etapa2'
    novo_status = data.get('status')
    
    grupo_producao = Grupo.query.filter_by(nome='Linha de Produção').first()
    grupo_instalados = Grupo.query.filter_by(nome='Instalados').first()

    if etapa == 'etapa1':
        orcamento.etapa1_status = novo_status
    elif etapa == 'etapa2':
        orcamento.etapa2_status = novo_status
    else:
        return jsonify({"error": "Etapa inválida"}), 400
        
    # --- REGRA DE AUTOMAÇÃO 1 ---
    if novo_status == 'Em Produção' and orcamento.grupo_id != grupo_producao.id:
        orcamento.grupo_id = grupo_producao.id
        
    # --- REGRA DE AUTOMAÇÃO 2 ---
    if orcamento.etapa1_status == 'Instalado' and orcamento.etapa2_status == 'Instalado':
        if grupo_instalados:
            orcamento.grupo_id = grupo_instalados.id
            
    db.session.commit()
    return jsonify(orcamento.to_dict())

@app.route('/api/tarefa/<int:tarefa_id>/status', methods=['PUT'])
def update_tarefa_status(tarefa_id):
    tarefa = TarefaProducao.query.get(tarefa_id)
    if not tarefa:
        return jsonify({"error": "Tarefa não encontrada"}), 404
        
    novo_status = request.json.get('status')
    tarefa.status = novo_status
    db.session.commit()
    
    # --- NOVA AUTOMAÇÃO: Checar se todas as tarefas do orçamento estão prontas ---
    orcamento = tarefa.orcamento
    todas_prontas = True
    if not orcamento.tarefas: # Se não houver tarefas (raro), não faz nada
        todas_prontas = False
        
    for t in orcamento.tarefas:
        if t.status != 'Produção Finalizada':
            todas_prontas = False
            break
            
    if todas_prontas:
        grupo_prontos = Grupo.query.filter_by(nome='Prontos para Instalação').first()
        if grupo_prontos:
            orcamento.grupo_id = grupo_prontos.id
            db.session.commit()

    # Retorna o ORÇAMENTO PAI, para o JS checar se o grupo mudou
    return jsonify(orcamento.to_dict())

@app.route('/api/orcamento/<int:orc_id>/move', methods=['PUT'])
def move_orcamento(orc_id):
    # Esta rota agora é usada apenas para movimentos manuais (ex: para Standby)
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    
    novo_grupo_id = request.json.get('novo_grupo_id')
    orcamento.grupo_id = novo_grupo_id
    db.session.commit()
    
    return jsonify(orcamento.to_dict())


# --- Comandos de CLI para setup ---
@app.cli.command('init-db')
def init_db_command():
    """Inicializa o banco de dados e cria os grupos fixos."""
    db.drop_all() # Cuidado: apaga tudo
    db.create_all()
    
    # Cria os grupos fixos na nova ordem
    g1 = Grupo(nome='Entrada de Orçamentos', ordem=1)
    g2 = Grupo(nome='Visitas e Medidas', ordem=2)
    g3 = Grupo(nome='Linha de Produção', ordem=3)
    g4 = Grupo(nome='Prontos para Instalação', ordem=4) # NOVO GRUPO
    g5 = Grupo(nome='Standby', ordem=5)
    g6 = Grupo(nome='Instalados', ordem=6)
    
    db.session.add_all([g1, g2, g3, g4, g5, g6])
    db.session.commit()
    print('Banco de dados inicializado e grupos criados.')

# Função de setup para rodar com 'python app.py'
def setup_database(app):
    with app.app_context():
        if not os.path.exists('workflow.db'):
             db.create_all()
             if not Grupo.query.first():
                g1 = Grupo(nome='Entrada de Orçamentos', ordem=1)
                g2 = Grupo(nome='Visitas e Medidas', ordem=2)
                g3 = Grupo(nome='Linha de Produção', ordem=3)
                g4 = Grupo(nome='Prontos para Instalação', ordem=4)
                g5 = Grupo(nome='Standby', ordem=5)
                g6 = Grupo(nome='Instalados', ordem=6)
                db.session.add_all([g1, g2, g3, g4, g5, g6])
                db.session.commit()
                print("DB e Grupos criados.")

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    setup_database(app)
    app.run(debug=True, port=5001)