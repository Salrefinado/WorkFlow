import os
import zipfile
import json
import requests
import threading
from urllib.parse import quote_plus
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# --- Configuração ---

app = Flask(__name__, template_folder='templates', static_folder='static')

# 1. Configuração do Banco de Dados (PostgreSQL no Render)
# Ele usará a variável de ambiente DATABASE_URL se existir, caso contrário, voltará para o sqlite local.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # O Render fornece 'postgres://' mas o SQLAlchemy prefere 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///workflow.db'

# 2. Configuração de Uploads (Render Disks)
# A variável RENDER_DISK_MOUNT_PATH será definida como '/var/data' no Render.
# Localmente, usará a pasta 'instance/persistent_uploads' para testes.
UPLOAD_DIR = os.environ.get('RENDER_DISK_MOUNT_PATH') or 'instance'
app.config['UPLOAD_FOLDER'] = os.path.join(UPLOAD_DIR, 'persistent_uploads')


db = SQLAlchemy(app)

# (NOVO) Garantir que a pasta de upload exista ANTES da primeira requisição
@app.before_request
def ensure_upload_folder_exists():
    upload_path = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_path):
        try:
            os.makedirs(upload_path)
        except OSError as e:
            app.logger.error(f"Erro ao criar pasta de upload {upload_path}: {e}")


# --- Configuração de Notificações (NOVO) ---
API_KEY = "9102015"
API_URL = "https://api.callmebot.com/whatsapp.php"
PHONE_ADMIN = "554188368319"
PHONE_PAULO = "554100000000"
PHONE_RENATO = "554100000001"

# Lista de destinatários
LISTA_GERAL = [PHONE_ADMIN, PHONE_PAULO, PHONE_RENATO]

# --- Função Auxiliar de Notificação (NOVO) ---

def send_whatsapp_notification(message, phone_numbers):
    """
    Envia uma notificação por WhatsApp para uma lista de números em threads separadas.
    """
    def send_request_target(phone, encoded_message):
        try:
            full_url = f"{API_URL}?phone={phone}&text={encoded_message}&apikey={API_KEY}"
            response = requests.get(full_url, timeout=10)
            print(f"Notificação enviada para {phone}. Status: {response.status_code}")
        except Exception as e:
            print(f"Erro ao enviar notificação para {phone}: {e}")

    try:
        encoded_message = quote_plus(message)
        
        if not isinstance(phone_numbers, list):
            phone_numbers = [phone_numbers]
            
        for phone in phone_numbers:
            # Inicia uma nova thread para cada requisição
            thread = threading.Thread(target=send_request_target, args=(phone, encoded_message))
            thread.start()
            
    except Exception as e:
        print(f"Erro ao preparar notificação: {e}")


# Mapeamento de Itens (do .ZIP) para Colaboradores (DETALhado)
ITEM_DEFINITIONS_PRODUCAO = {
    "Tampa Inox": "Anderson",
    "Tampa Epoxi": "Anderson",
    "Revestimento Fundo": "Hélio",
    "Revestimento Em L": "Hélio",
    "Revestimento Em U": "Hélio",
    "Sistema de Elevar Manual 2 3/16": "Luiz e José",
    "Sistema de Elevar Manual 1/8 e 3/16": "Luiz e José",
    "Sistema de Elevar Manual Arg e 3/16": "Luiz e José",
    "Sistema de Elevar Manual Arg e 1/8": "Luiz e José",
    "Sistema de Elevar Motor 2 3/16": "Luiz e José",
    "Sistema de Elevar Motor 1/8 e 3/16": "Luiz e José",
    "Sistema de Elevar Motor Arg e 3/16": "Luiz e José",
    "Sistema de Elevar Motor Arg e 1/8": "Luiz e José",
    "Giratório 1L 4E": "Luiz",
    "Giratório 1L 5E": "Luiz",
    "Giratório 2L 5E": "Luiz",
    "Giratório 2L 6E": "Luiz",
    "Giratório 2L 7E": "Luiz",
    "Giratório 2L 8E": "Luiz",
    "Cooktop + Bifeira": "Luiz",
    "Cooktop": "Indefinido",
    "Porta Guilhotina Vidro L": "Edison",
    "Porta Guilhotina Vidro U": "Edison",
    "Porta Guilhotina Vidro F": "Edison",
    "Porta Guilhotina Inox F": "Edison",
    "Porta Guilhotina Pedra F": "Edison",
    "Coifa Epoxi": "Hélio",
    "Isolamento Coifa": "Indefinido",
    "Placa cimenticia Porta": "Edison",
    "Revestimento Base": "Indefinido",
    "Bifeteira grill": "Luiz",
    "Balanço 2": "Luiz",
    "Balanço 3": "Luiz",
    "Balanço 4": "Luiz",
    "Kit 6 Espetos": "José",
    "Regulagem Comum 2": "José",
    "Regulagem Comum 3": "José",
    "Regulagem Comum 4": "José",
    "Regulagem Comum 5": "José",
    "Gavetão Inox": "Hélio",
    "Moldura Área de fogo": "Luiz",
    "Grelha de descanso": "José",
    "KAM800 2 Faces": "Edison"
}

# NOVO: Mapeamento de Itens (CRIAÇÃO MANUAL) para Colaboradores (SIMPLIFICADO)
MANUAL_ITEM_MAP = {
    # Edison
    "Porta Guilhotina": "Edison",
    "Tampa Vidro": "Edison",
    "Lareira": "Edison",
    # Luiz
    "Parrila": "Luiz",
    "Regulagem de Balanço": "Luiz",
    "Giratorio": "Luiz",
    "Sistema Motor": "Luiz",
    "Moldura": "Luiz",
    "Base": "Luiz",
    # Hélio
    "Coifa e Chaminé": "Hélio",
    "Coifa": "Hélio",
    "Gavetão": "Hélio",
    "Revestimento": "Hélio",
    # José
    "Grelhas": "José",
    "Espetos": "José",
    "Sistema Elevar Manual": "José",
    # Anderson
    "Chaminé Lareira": "Anderson",
    "Tampa Churrasqueira": "Anderson"
}


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
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    
    status_atual = db.Column(db.String(100), default='Orçamento Aprovado')
    
    data_entrada_producao = db.Column(db.DateTime)
    data_limite_producao = db.Column(db.DateTime)
    
    data_visita = db.Column(db.DateTime)
    responsavel_visita = db.Column(db.String(100))
    
    data_pronto = db.Column(db.DateTime)
    data_instalacao = db.Column(db.DateTime)
    responsavel_instalacao = db.Column(db.String(100))
    
    grupo_origem_standby = db.Column(db.Integer)
    
    etapa1_descricao = db.Column(db.String(500))
    etapa2_descricao = db.Column(db.String(500))
    
    tarefas = db.relationship('TarefaProducao', backref='orcamento', lazy=True, cascade="all, delete-orphan")
    arquivos = db.relationship('ArquivoAnexado', backref='orcamento', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "cliente": self.cliente,
            "grupo_id": self.grupo_id,
            "grupo_nome": self.grupo.nome,
            
            "status_atual": self.status_atual,
            "data_entrada_producao": self.data_entrada_producao.strftime('%Y-%m-%d') if self.data_entrada_producao else None,
            "data_limite_producao": self.data_limite_producao.strftime('%Y-%m-%d') if self.data_limite_producao else None,
            
            "data_visita": self.data_visita.strftime('%Y-%m-%d %H:%M') if self.data_visita else None,
            "responsavel_visita": self.responsavel_visita,
            "data_pronto": self.data_pronto.strftime('%Y-%m-%d %H:%M') if self.data_pronto else None,
            "data_instalacao": self.data_instalacao.strftime('%Y-%m-%d %H:%M') if self.data_instalacao else None,
            "responsavel_instalacao": self.responsavel_instalacao,
            "grupo_origem_standby": self.grupo_origem_standby,
            
            "etapa1_descricao": self.etapa1_descricao,
            "etapa2_descricao": self.etapa2_descricao,

            # MODIFICAÇÃO: Ordenar tarefas por colaborador e depois por item
            "tarefas": sorted([t.to_dict() for t in self.tarefas], key=lambda x: (x['colaborador'], x['item_descricao'])),
            "arquivos": [a.to_dict() for a in self.arquivos]
        }

class TarefaProducao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    colaborador = db.Column(db.String(100), nullable=False)
    item_descricao = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Não Iniciado')
    
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
    # (MODIFICADO) Não armazenamos mais o caminho, apenas o nome do arquivo.
    # caminho_arquivo = db.Column(db.String(500))

    def to_dict(self):
        return {
            "id": self.id,
            "nome_arquivo": self.nome_arquivo,
            # (MODIFICADO) A URL é gerada dinamicamente
            "url": f"/uploads/{self.nome_arquivo}"
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
        # Ordenar orçamentos dentro do grupo (opcional, mas bom para consistência)
        # ... (lógica de ordenação se necessário) ...
        workflow_data.append({
            "id": grupo.id,
            "nome": grupo.nome,
            "orcamentos": orcamentos_data
        })
    return jsonify(workflow_data)

# ATUALIZADO: Rota de criação manual
@app.route('/api/orcamento/create_manual', methods=['POST'])
def create_orcamento_manual():
    try:
        # Pega dados do formulário (request.form)
        numero = request.form.get('numero_orcamento')
        cliente = request.form.get('nome_cliente')
        
        # Pega os itens selecionados (enviados pelo JS)
        etapa1_desc = request.form.get('etapa1_descricao') # String com todos os itens
        production_items_json = request.form.get('production_items') # Lista JSON de itens
        items_list = [] # (NOVO)

        if not numero or not cliente:
            return jsonify({"error": "Número do Orçamento e Nome do Cliente são obrigatórios."}), 400

        # Cria o novo orçamento
        novo_orcamento = Orcamento(
            numero=numero,
            cliente=cliente,
            etapa1_descricao=etapa1_desc, # Salva a string de itens para visibilidade
            etapa2_descricao="", # Campo não mais usado no modal, mas pode ser mantido
            grupo_id=1, # ID 1 = "Entrada de Orçamento"
            status_atual='Orçamento Aprovado'
        )
        db.session.add(novo_orcamento)
        db.session.commit() # Salva para obter o ID

        # Processa o arquivo (se houver)
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and file.filename != '':
                safe_filename = secure_filename(file.filename)
                # (MODIFICADO) Salva no UPLOAD_FOLDER configurado
                target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                file.save(target_path)
                
                anexo = ArquivoAnexado(
                    orcamento_id=novo_orcamento.id,
                    nome_arquivo=safe_filename
                    # (MODIFICADO) Não salva mais o caminho
                )
                db.session.add(anexo)

        # Processa os ITENS DE PRODUÇÃO
        if production_items_json:
            items_list = json.loads(production_items_json) # (NOVO) Carrega a lista
            for item_desc in items_list:
                # Usa o NOVO MAPA para encontrar o colaborador
                colaborador = MANUAL_ITEM_MAP.get(item_desc, "Indefinido")
                
                # Cria a Tarefa de Produção
                tarefa = TarefaProducao(
                    orcamento_id=novo_orcamento.id,
                    colaborador=colaborador,
                    item_descricao=item_desc,
                    status='Não Iniciado' # Padrão
                )
                db.session.add(tarefa)

        db.session.commit() # Salva o anexo e as tarefas
        
        # --- (NOVO) Notificação ---
        itens_str = ", ".join(items_list) if items_list else "Nenhum"
        # (NOVO) ATUALIZAÇÃO DE TEMPLATE
        message = (
            f"🆕 Novo Orçamento Recebido!\n\n"
            f"👤 Cliente: {numero} {cliente}\n"
            f"🧾 Itens: {itens_str}\n"
            f"📁 Status: {novo_orcamento.status_atual}"
        )
        send_whatsapp_notification(message, [PHONE_ADMIN])
        # --- Fim Notificação ---
        
        return jsonify(novo_orcamento.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_orcamento():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({"error": "Arquivo inválido, envie um .zip"}), 400

    json_data = None
    pdf_files = []
    
    # (NOVO) Para notificação
    itens_producao_desc = []

    try:
        with zipfile.ZipFile(file, 'r') as zf:
            for filename in zf.namelist():
                if filename.endswith('.json'):
                    with zf.open(filename) as f:
                        json_data = json.load(f)
                elif filename.endswith('.pdf'):
                    safe_filename = secure_filename(os.path.basename(filename))
                    # (MODIFICADO) Salva no UPLOAD_FOLDER configurado
                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                    with open(target_path, 'wb') as f:
                        f.write(zf.read(filename))
                    # (MODIFICADO) Salva apenas o nome do arquivo
                    pdf_files.append({"nome": safe_filename})

        if not json_data:
            return jsonify({"error": "Arquivo .json não encontrado no .zip"}), 400

        novo_orcamento = Orcamento(
            numero=json_data.get('numero_orcamento', 'N/A'),
            cliente=json_data.get('nome_cliente', 'N/A'),
            grupo_id=1, 
            status_atual='Orçamento Aprovado',
            etapa1_descricao=json_data.get('itens_etapa_1', ''),
            etapa2_descricao=json_data.get('itens_etapa_2', '')
        )
        db.session.add(novo_orcamento)
        db.session.commit()
        
        for pdf in pdf_files:
            anexo = ArquivoAnexado(
                orcamento_id=novo_orcamento.id,
                nome_arquivo=pdf['nome']
                # (MODIFICADO) Não salva mais o caminho
            )
            db.session.add(anexo)

        # Lógica de Tarefas (Upload ZIP usa o mapa antigo e detalhado)
        if 'tarefas_producao' in json_data:
            for tarefa_info in json_data['tarefas_producao']:
                item_desc = tarefa_info.get('item', 'Item não descrito')
                itens_producao_desc.append(item_desc) # (NOVO) Adiciona para notificação
                
                # Usa o MAPA ANTIGO (detalhado) para .zip
                colaborador_definido = ITEM_DEFINITIONS_PRODUCAO.get(item_desc, "Indefinido")
                
                tarefa = TarefaProducao(
                    orcamento_id=novo_orcamento.id,
                    colaborador=colaborador_definido,
                    item_descricao=item_desc
                )
                db.session.add(tarefa)
        
        db.session.commit()
        
        # --- (NOVO) Notificação ---
        itens_str = ", ".join(itens_producao_desc) if itens_producao_desc else "Nenhum"
        # (NOVO) ATUALIZAÇÃO DE TEMPLATE
        message = (
            f"🆕 Novo Orçamento Recebido!\n\n"
            f"👤 Cliente: {novo_orcamento.numero} {novo_orcamento.cliente}\n"
            f"🧾 Itens: {itens_str}\n"
            f"📁 Status: {novo_orcamento.status_atual}"
        )
        send_whatsapp_notification(message, [PHONE_ADMIN])
        # --- Fim Notificação ---
        
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
        # (MODIFICADO) Salva no UPLOAD_FOLDER configurado
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(target_path)
        
        anexo = ArquivoAnexado(
            orcamento_id=orcamento.id,
            nome_arquivo=safe_filename
            # (MODIFICADO) Não salva mais o caminho
        )
        db.session.add(anexo)
        db.session.commit()
        
        return jsonify(anexo.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# (MODIFICADO) Esta rota agora serve arquivos da pasta de upload persistente
@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    # Serve arquivos diretamente do UPLOAD_FOLDER configurado (que será o disco persistente)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def parse_datetime(date_str):
    if not date_str: return None
    try:
        # Tenta formatar '2023-10-31T14:30'
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            # Tenta formatar '2023-10-31'
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None

@app.route('/api/orcamento/<int:orc_id>/status', methods=['PUT'])
def update_orcamento_status(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: 
        return jsonify({"error": "Orçamento não encontrado"}), 404
        
    data = request.json
    novo_status = data.get('novo_status')
    dados_adicionais = data.get('dados_adicionais', {})
    
    # --- (NOVO) Captura dados antigos para notificação ---
    status_antigo = orcamento.status_atual
    grupo_atual_id = orcamento.grupo_id
    grupo_antigo_nome = orcamento.grupo.nome
    # --- Fim Captura ---
    
    orcamento.status_atual = novo_status
    
    grupos = {g.nome: g.id for g in Grupo.query.all()}
    g_entrada = grupos.get('Entrada de Orçamento')
    g_visitas = grupos.get('Visitas e Medidas')
    g_projetar = grupos.get('Projetar')
    g_producao = grupos.get('Linha de Produção')
    g_prontos = grupos.get('Prontos')
    g_standby = grupos.get('StandBy')
    g_instalados = grupos.get('Instalados')
    
    moveu_para_producao = False
    
    # (NOVO) Variáveis de notificação
    notification_message = None
    notification_recipients = []

    if grupo_atual_id == g_entrada:
        # (NOVO) Trigger 2: Mudança no grupo "Entrada"
        notification_recipients = LISTA_GERAL
        # (NOVO) ATUALIZAÇÃO DE TEMPLATE
        notification_message = f"📋 Atualização de Orçamento\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔄 Mudou o status de: {status_antigo}\n\n➡️ Para: {novo_status}"

        if novo_status == 'Visita Agendada':
            orcamento.grupo_id = g_visitas
            orcamento.data_visita = parse_datetime(dados_adicionais.get('data_visita'))
            orcamento.responsavel_visita = dados_adicionais.get('responsavel_visita')
        elif novo_status in ['Desenhar', 'Produzir']:
            orcamento.grupo_id = g_projetar
        elif novo_status == 'Em Produção':
            orcamento.grupo_id = g_producao
            moveu_para_producao = True
        elif novo_status in ['Aguardando Cliente', 'Aguardando Arq/Eng', 'Aguardando Obra', 'Parado']:
            orcamento.grupo_id = g_standby
            orcamento.grupo_origem_standby = grupo_atual_id

    elif grupo_atual_id == g_visitas:
        if novo_status == 'Mandar para Produção':
            orcamento.grupo_id = g_projetar
        elif novo_status == 'Em Produção':
            orcamento.grupo_id = g_producao
            moveu_para_producao = True
        elif novo_status == 'Instalado':
            etapa = dados_adicionais.get('etapa_instalada')
            if etapa == 'Etapa 1':
                orcamento.grupo_id = g_visitas
                orcamento.status_atual = 'Agendar Visita'
            elif etapa == 'Etapa 2':
                orcamento.grupo_id = g_instalados
                orcamento.status_atual = 'Instalado'

    elif grupo_atual_id == g_projetar:
        if novo_status == 'Aprovado para Produção':
            orcamento.grupo_id = g_producao
            moveu_para_producao = True
        elif novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.grupo_origem_standby = grupo_atual_id

    elif grupo_atual_id == g_producao:
        if novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.grupo_origem_standby = grupo_atual_id

    elif grupo_atual_id == g_prontos:
        if novo_status == 'Instalação Agendada':
            orcamento.data_instalacao = parse_datetime(dados_adicionais.get('data_instalacao'))
            orcamento.responsavel_instalacao = dados_adicionais.get('responsavel_instalacao')
        elif novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.grupo_origem_standby = grupo_atual_id
        elif novo_status == 'Instalado':
            etapa = dados_adicionais.get('etapa_instalada')
            if etapa == 'Etapa 1':
                orcamento.grupo_id = g_visitas
                orcamento.status_atual = 'Agendar Visita'
            elif etapa == 'Etapa 2':
                orcamento.grupo_id = g_instalados
                orcamento.status_atual = 'Instalado'

    elif grupo_atual_id == g_standby:
        # (NOVO) Trigger 7: Mudança no grupo "Standby"
        notification_recipients = LISTA_GERAL
        # (NOVO) ATUALIZAÇÃO DE TEMPLATE
        notification_message = f"🔄 Atualização de Status\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Mudou o status de: {status_antigo}\n\n➡️ Para: {novo_status}"

        if novo_status == 'Liberado':
            if orcamento.grupo_origem_standby:
                orcamento.grupo_id = orcamento.grupo_origem_standby
            else:
                orcamento.grupo_id = g_entrada
            orcamento.grupo_origem_standby = None
    
    elif grupo_atual_id == g_instalados:
        # (NOVO) Trigger 7: Mudança no grupo "Instalados"
        notification_recipients = LISTA_GERAL
        # (NOVO) ATUALIZAÇÃO DE TEMPLATE
        notification_message = f"🔄 Atualização de Status\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Mudou o status de: {status_antigo}\n\n➡️ Para: {novo_status}"
            
    if moveu_para_producao:
        orcamento.data_entrada_producao = parse_datetime(dados_adicionais.get('data_entrada'))
        orcamento.data_limite_producao = parse_datetime(dados_adicionais.get('data_limite'))
        for tarefa in orcamento.tarefas:
            tarefa.status = 'Não Iniciado'
    
    try:
        db.session.commit()
        
        # --- (NOVO) Lógica de Notificação Pós-Commit ---
        
        # (Trigger 2) Complemento - Checa se moveu de grupo
        if notification_message and grupo_atual_id == g_entrada and orcamento.grupo_id != grupo_atual_id:
            grupo_novo_nome = orcamento.grupo.nome
            # (NOVO) ATUALIZAÇÃO DE TEMPLATE (MOVIMENTO)
            notification_message = f"📋 Atualização de Orçamento\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔄 Mudou o status de: {status_antigo}\n\n➡️ Para: {novo_status}\n\n📁 E foi movido para o grupo: {grupo_novo_nome}"

        # (Trigger 3) Agendamento de Visita
        if novo_status == 'Visita Agendada':
            data_visita_fmt = orcamento.data_visita.strftime('%d/%m %H:%M') if orcamento.data_visita else 'N/A'
            # (NOVO) ATUALIZAÇÃO DE TEMPLATE
            notification_message = f"📆 Visita Agendada!\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Data: {data_visita_fmt}\n\n👷 Responsável: {orcamento.responsavel_visita}"
            notification_recipients = LISTA_GERAL

        # (Trigger 4) Agendamento de Instalação
        elif novo_status == 'Instalação Agendada':
            data_inst_fmt = orcamento.data_instalacao.strftime('%d/%m %H:%M') if orcamento.data_instalacao else 'N/A'
            # (NOVO) ATUALIZAÇÃO DE TEMPLATE
            notification_message = f"🔧 Instalação Agendada!\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Data: {data_inst_fmt}\n\n👷 Responsável: {orcamento.responsavel_instalacao}"
            notification_recipients = LISTA_GERAL
        
        # (Trigger 6) Instalação Concluída
        elif novo_status == 'Instalado' and (grupo_atual_id == g_visitas or grupo_atual_id == g_prontos):
            etapa = dados_adicionais.get('etapa_instalada', 'N/A')
            etapa_num = "1ª" if etapa == 'Etapa 1' else "2ª"
            resp_inst = orcamento.responsavel_instalacao or 'N/A'
            # (NOVO) ATUALIZAÇÃO DE TEMPLATE
            notification_message = f"🎉 Instalação Concluída!\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔧 Etapa: {etapa_num} Etapa\n\n👷 Responsável: {resp_inst}"
            
            if etapa == 'Etapa 1':
                 notification_message += "\n\n📁 Movido para Visitas e Medidas — agendar a visita para medidas da segunda etapa."
                 
            notification_recipients = LISTA_GERAL
        
        # Envia a notificação se houver
        if notification_message and notification_recipients:
            send_whatsapp_notification(notification_message, notification_recipients)
        # --- Fim Notificação ---
        
        return jsonify(orcamento.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tarefa/<int:tarefa_id>/status', methods=['PUT'])
def update_tarefa_status(tarefa_id):
    tarefa = TarefaProducao.query.get(tarefa_id)
    if not tarefa:
        return jsonify({"error": "Tarefa não encontrada"}), 404
        
    novo_status = request.json.get('status')
    
    # (NOVO) Captura dados para notificação
    orcamento = tarefa.orcamento
    numero = orcamento.numero
    cliente = orcamento.cliente
    colaborador = tarefa.colaborador
    item = tarefa.item_descricao
    notification_message = None
    
    tarefa.status = novo_status
    db.session.commit()
    
    todas_prontas = True
    if not orcamento.tarefas:
        todas_prontas = False
        
    for t in orcamento.tarefas:
        if t.status != 'Produção Finalizada':
            todas_prontas = False
            break
            
    if todas_prontas:
        grupo_prontos = Grupo.query.filter_by(nome='Prontos').first()
        if grupo_prontos and orcamento.grupo_id != grupo_prontos.id:
            orcamento.grupo_id = grupo_prontos.id
            orcamento.data_pronto = datetime.utcnow()
            orcamento.status_atual = 'Agendar Instalação/Entrega'
            db.session.commit()
            
    # --- (NOVO) Notificação de Tarefa (Trigger 5) ---
    if novo_status == 'Iniciou a Produção':
        notification_message = f"⚙️ Início de Produção\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n🚀 Itens iniciados: {item}"
    elif novo_status == 'Fase de Acabamento':
        notification_message = f"🛠️ Atualização de Produção\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n🎨 Itens em fase de acabamento: {item}"
    elif novo_status == 'Produção Finalizada':
        notification_message = f"✅ Produção Concluída!\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n📦 Itens finalizados: {item}"
        if todas_prontas:
             notification_message += "\n\n📁 Movido para o grupo: Prontos\n\n📅 Agende uma data de instalação ou entrega."
    elif novo_status == 'Aguardando Vidro / Pedra':
        notification_message = f"📦 Aguardando Materiais\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n🪟 Situação: Aguardando vidro/pedra para iniciar a produção."
    elif novo_status == 'Reforma em Andamento':
        notification_message = f"🔨 Reforma em Andamento\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n🔁 Situação: Reforma em andamento na linha de produção."
    elif novo_status == 'StandBy':
        notification_message = f"⏸️ Produção em StandBy\n\n👤 Cliente: {numero} {cliente}\n\n🧑‍🏭 Responsável: {colaborador}\n\n📦 Situação: Projeto pausado temporariamente."

    if notification_message:
        send_whatsapp_notification(notification_message, LISTA_GERAL)
    # --- Fim Notificação ---

    return jsonify(orcamento.to_dict())

@app.route('/api/orcamento/<int:orc_id>/move', methods=['PUT'])
def move_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    
    data = request.json
    novo_grupo_id = int(data.get('novo_grupo_id'))
    if orcamento.grupo_id == novo_grupo_id:
        return jsonify(orcamento.to_dict())

    # (NOVO) Captura dados para notificação
    grupo_antigo_nome = orcamento.grupo.nome
    
    grupo_destino = Grupo.query.get(novo_grupo_id)
    if not grupo_destino:
        return jsonify({"error": "Grupo de destino não encontrado"}), 404

    # (NOVO) Captura nome do novo grupo
    grupo_novo_nome = grupo_destino.nome
    
    orcamento.grupo_id = novo_grupo_id
    
    if grupo_destino.nome == 'Entrada de Orçamento':
        orcamento.status_atual = 'Orçamento Aprovado'
    elif grupo_destino.nome == 'Visitas e Medidas':
        orcamento.status_atual = 'Agendar Visita'
    elif grupo_destino.nome == 'Projetar':
        orcamento.status_atual = 'Em Desenho'
    elif grupo_destino.nome == 'Linha de Produção':
        orcamento.status_atual = 'Não Iniciado' # (Mudança) O status padrão é "Não Iniciado"
        orcamento.data_entrada_producao = parse_datetime(data.get('data_entrada'))
        orcamento.data_limite_producao = parse_datetime(data.get('data_limite'))
        for tarefa in orcamento.tarefas:
            tarefa.status = 'Não Iniciado'
    elif grupo_destino.nome == 'Prontos':
        orcamento.status_atual = 'Agendar Instalação/Entrega'
        if not orcamento.data_pronto:
             orcamento.data_pronto = datetime.utcnow()
    elif grupo_destino.nome == 'StandBy':
        orcamento.status_atual = 'Parado' # (Mudança) Status padrão de Standby
        # Bug fix: Nao setar grupo origem se ja estiver em standby
        if orcamento.grupo_origem_standby is None:
            # (Correção) Deve pegar o ID do grupo antigo, não o ID do grupo atual (que já é standby)
            grupo_antigo_id = Grupo.query.filter_by(nome=grupo_antigo_nome).first().id
            orcamento.grupo_origem_standby = grupo_antigo_id
    elif grupo_destino.nome == 'Instalados':
        orcamento.status_atual = 'Instalado'
        
    db.session.commit()
    
    # --- (NOVO) Notificação de Arrastar (Trigger 8) ---
    # (NOVO) ATUALIZAÇÃO DE TEMPLATE
    message = f"↔️ Item Movido Manualmente\n\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📁 Movido de: {grupo_antigo_nome}\n\n➡️ Para: {grupo_novo_nome}"
    send_whatsapp_notification(message, LISTA_GERAL)
    # --- Fim Notificação ---
    
    return jsonify(orcamento.to_dict())

# --- NOVO: Rota para adicionar tarefa de produção ---
@app.route('/api/orcamento/<int:orc_id>/add_tarefa', methods=['POST'])
def add_tarefa_to_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
        
    data = request.json
    colaborador = data.get('colaborador')
    item_descricao = data.get('item_descricao')
    
    if not colaborador or not item_descricao:
        return jsonify({"error": "Colaborador e Item são obrigatórios"}), 400
        
    try:
        nova_tarefa = TarefaProducao(
            orcamento_id=orc_id,
            colaborador=colaborador,
            item_descricao=item_descricao,
            status='Não Iniciado' # Padrão
        )
        db.session.add(nova_tarefa)
        db.session.commit()
        return jsonify(nova_tarefa.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Comandos de CLI para setup ---
@app.cli.command('init-db')
def init_db_command():
    """Inicializa o banco de dados e cria os grupos fixos."""
    db.drop_all()
    db.create_all()
    
    g1 = Grupo(nome='Entrada de Orçamento', ordem=1)
    g2 = Grupo(nome='Visitas e Medidas', ordem=2)
    g3 = Grupo(nome='Projetar', ordem=3)
    g4 = Grupo(nome='Linha de Produção', ordem=4)
    g5 = Grupo(nome='Prontos', ordem=5)
    g6 = Grupo(nome='StandBy', ordem=6)
    g7 = Grupo(nome='Instalados', ordem=7)
    
    db.session.add_all([g1, g2, g3, g4, g5, g6, g7])
    db.session.commit()
    print('Banco de dados inicializado e grupos (7) criados.')

def setup_database(app):
    with app.app_context():
        # (MODIFICADO) Não verifica mais o 'workflow.db' pois usará o Postgres
        # if not os.path.exists('workflow.db'):
        
        # Apenas cria as tabelas se não existirem (o init-db fará a criação dos grupos)
        db.create_all()
        
        # Lógica de criação de grupo movida para 'init-db' para ser executada manualmente no deploy
        if not Grupo.query.first():
            print("Banco de dados vazio. Execute 'flask init-db' para popular os grupos.")
            # g1 = Grupo(nome='Entrada de Orçamento', ordem=1)
            # ... (etc) ...
            # db.session.commit()
            # print("DB e Grupos criados.")

if __name__ == '__main__':
    # (MODIFICADO) Não cria mais a pasta 'uploads' aqui, é feito pelo @app.before_request
    # if not os.path.exists('uploads'):
    #     os.makedirs('uploads')
    setup_database(app)
    # (MODIFICADO) Define a porta com base no ambiente, padrão 5001 localmente
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, port=port) # debug=True é OK para local, Render ignora
