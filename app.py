import os
from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime

app = Flask(__name__)

# --- Configurações do Banco de Dados ---
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise # Mantemos o raise para que o erro seja visível no log do Render

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                due_date TEXT
            );
        ''')
        conn.commit()
        cur.close()
        print("Banco de dados inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

# --- NOVA ROTA DE TESTE ---
@app.route('/', methods=['GET'])
def home():
    """Rota de teste para verificar se a aplicação está no ar."""
    return "Bem-vindo à API de Tarefas!", 200
# --- FIM DA NOVA ROTA DE TESTE ---


# --- Funções de Validação (sem alterações) ---
def validate_date(date_str):
    if not date_str:
        return True
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_status(status):
    return status in ['pendente', 'realizando', 'concluída']

# --- Rotas da API (sem alterações, exceto os print para depuração) ---

@app.route('/tarefas', methods=['POST'])
def create_task():
    data = request.get_json()
    title = data.get('titulo')
    description = data.get('descricao')
    status = data.get('status')
    due_date = data.get('data_vencimento')

    if not title or not status:
        return jsonify({'error': 'Título e status são obrigatórios'}), 400

    if not validate_status(status):
        return jsonify({'error': 'Status inválido'}), 400

    if due_date and not validate_date(due_date):
        return jsonify({'error': 'Data de vencimento inválida'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (title, description, status, due_date)
            VALUES (%s, %s, %s, %s) RETURNING id;
        ''', (title, description, status, due_date))
        task_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return jsonify({
            'id': task_id,
            'titulo': title,
            'descricao': description,
            'status': status,
            'data_vencimento': due_date
        }), 201
    except Exception as e:
        print(f"Erro ao criar tarefa: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/tarefas', methods=['GET'])
def list_tasks():
    status = request.args.get('status')
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if status and validate_status(status):
            cursor.execute('SELECT id, title, description, status, due_date FROM tasks WHERE status = %s', (status,))
        else:
            cursor.execute('SELECT id, title, description, status, due_date FROM tasks')

        tasks = [{
            'id': row[0],
            'titulo': row[1],
            'descricao': row[2],
            'status': row[3],
            'data_vencimento': row[4]
        } for row in cursor.fetchall()]
        cursor.close()
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Erro ao listar tarefas: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/tarefas/<int:id>', methods=['GET'])
def get_task(id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, status, due_date FROM tasks WHERE id = %s', (id,))
        task = cursor.fetchone()
        cursor.close()
        if not task:
            return jsonify({'error': 'Tarefa não encontrada'}), 404

        return jsonify({
            'id': task[0],
            'titulo': task[1],
            'descricao': task[2],
            'status': task[3],
            'data_vencimento': task[4]
        }), 200
    except Exception as e:
        print(f"Erro ao obter tarefa: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/tarefas/<int:id>', methods=['PUT'])
def update_task(id):
    data = request.get_json()
    title = data.get('titulo')
    description = data.get('descricao')
    status = data.get('status')
    due_date = data.get('data_vencimento')

    if not title or not status:
        return jsonify({'error': 'Título e status são obrigatórios'}), 400

    if not validate_status(status):
        return jsonify({'error': 'Status inválido'}), 400

    if due_date and not validate_date(due_date):
        return jsonify({'error': 'Data de vencimento inválida'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tasks WHERE id = %s', (id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Tarefa não encontrada'}), 404

        cursor.execute('''
            UPDATE tasks
            SET title = %s, description = %s, status = %s, due_date = %s
            WHERE id = %s;
        ''', (title, description, status, due_date, id))
        conn.commit()
        cursor.close()
        return jsonify({
            'id': id,
            'titulo': title,
            'descricao': description,
            'status': status,
            'data_vencimento': due_date
        }), 200
    except Exception as e:
        print(f"Erro ao atualizar tarefa: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/tarefas/<int:id>', methods=['DELETE'])
def delete_task(id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tasks WHERE id = %s', (id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Tarefa não encontrada'}), 404

        cursor.execute('DELETE FROM tasks WHERE id = %s', (id,))
        conn.commit()
        cursor.close()
        return jsonify({'message': 'Tarefa excluída com sucesso'}), 200
    except Exception as e:
        print(f"Erro ao deletar tarefa: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
