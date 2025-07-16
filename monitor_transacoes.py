import cx_Oracle
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações do Banco de Dados e E-mail (carregadas do .env) ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("email_port", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO").split(',') # Converte a string de e-mails em uma lista

def verificar_transacoes():
    """
    Conecta ao banco de dados, executa a consulta e retorna os resultados.
    """
    try:
        # Inicializa o cliente Oracle, se necessário
        # cx_Oracle.init_oracle_client(lib_dir=r"C:\path\to\your\instantclient") # Descomente e ajuste o caminho se necessário

        connection = cx_Oracle.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()

        query = """
            SELECT 
                t.nr_transacao,
                t.dt_transacao,
                t.cd_operador,
                tc.nr_contagem,
                gc.cd_produto,
                pcr.cd_rfid,
                pcr.tp_situacao
            
            FROM
                TRA_TRANSACAO t
            JOIN 
                TRA_TRANSACCONT tc ON t.nr_transacao = tc.nr_transacao AND t.cd_empresa = tc.cd_emptransacao
            JOIN
                GER_CONTAGEMI gc ON tc.nr_contagem = gc.nr_contagem AND t.cd_empresa = gc.cd_empresa
            JOIN
                PRD_CODIGORFID pcr ON gc.cd_produto = pcr.cd_produto
            WHERE
                t.cd_empresa = 2
                AND t.tp_situacao = 4
                AND t.tp_operacao = 'S'
                AND t.cd_operacao' IN (551, 556, 557)
                AND pcr.tp_situacao <> 1
        """
        cursor.execute(query)
        resultados = cursor.fetchall()

        # Obter os nomes das colunas para formatação
        colunas = [desc[0] for desc in cursor.description]
        
        cursor.close()
        connection.close()

        # Formatar resultados com uma lista de dicionários
        resultados_formatados = [dict(zip(colunas, row)) for row in resultados]
        return resultados_formatados
    
    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ou executar a consulta no Oracle: {error}")
        return None