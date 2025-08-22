import cx_Oracle
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações (sem alterações) ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO").split(',')

# ===== NOVAS CONSTANTES PARA O LOG =====
CODIGO_ROTINA = 7
STATUS_INICIO = 1
STATUS_FIM = 2
INTERVALO_SEGUNDOS = 60

def registrar_log_execucao(codigo_rotina , status):
    """
    Conecta ao banco e chama a procedure para registrar o início ou fim da execução.
    """
    connection = None
    try:
        connection = cx_Oracle.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()

        # Define o nome do status para uma mensagem de log mais clara
        nome_status = "INÍCIO" if status == STATUS_INICIO else "FIM"

        print(f"Registrando log de {nome_status} para a rotina {codigo_rotina}...")
        cursor.callproc("bgintegra.P_BGR_HIST_ROTINAS_INT", [codigo_rotina, status])
        print("Log registrado com sucesso.")
    
    except cx_Oracle.Error as error:
        print(f"ERRO ao registrar log no banco de dados: {error}")
    finally:
        if connection:
            connection.close()

def verificar_transacoes():
    """
    Conecta ao banco de dados, executa a consulta e retorna os resultados.
    """
    try:
        connection = cx_Oracle.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()

        # ***** QUERY FINAL E SIMPLIFICADA *****
        query = """
            SELECT
                t.nr_transacao,
                t.dt_transacao,
                t.cd_operador,
                u.nm_login AS nm_operador,
                tc.nr_contagem,
                gc.cd_produto,
                pcr.cd_rfid,
                CASE pcr.tp_situacao
                    WHEN 2 THEN '2 - Em Producao'
                    WHEN 3 THEN '3 - Em Contagem'
                    WHEN 4 THEN '4 - Encerrado'
                    WHEN 5 THEN '5 - Agrupado'
                    WHEN 6 THEN '6 - Cancelado'
                    ELSE TO_CHAR(pcr.tp_situacao) || ' - Status Desconhecido'
                END AS ds_situacao_rfid
            FROM
                TRA_TRANSACAO t
            JOIN
                TRA_TRANSACCONT tc ON t.nr_transacao = tc.nr_transacao AND t.cd_empresa = tc.cd_emptransacao
            JOIN
                GER_CONTAGEMI gc ON tc.nr_contagem = gc.nr_contagem AND t.cd_empresa = gc.cd_empresa
            JOIN
                PRD_CODIGORFID pcr ON gc.cd_barraprd = pcr.cd_rfid AND gc.cd_produto = pcr.cd_produto
            JOIN
                ADM_USUARIO u ON t.cd_operador = u.cd_usuario
            WHERE
                t.cd_empresa = 2
                AND t.tp_situacao = 4
                AND t.tp_operacao = 'S'
                AND t.cd_operacao IN (551, 556, 557)
                AND t.dt_transacao >= TRUNC(SYSDATE)
                -- A regra de negócio final e simplificada:
                AND pcr.tp_situacao NOT IN (1, 3, 4)
            ORDER BY
                t.nr_transacao, pcr.cd_rfid
        """
        cursor.execute(query)
        resultados = cursor.fetchall()

        colunas = [desc[0] for desc in cursor.description]
        cursor.close()
        connection.close()
        
        resultados_formatados = [dict(zip(colunas, row)) for row in resultados]
        return resultados_formatados

    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ou executar a consulta no Oracle: {error}")
        return None

def enviar_email(inconsistencias):
    # A função de envio de email não precisa de alterações
    if not inconsistencias:
        return

    corpo_html = """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Alerta de Inconsistência na Transação de Saída</h2>
        <p>Foram identificados produtos com situação de RFID inválida para o processo de expedição (ex: Em Produção, Cancelado, etc.). Por favor, verifiquem os itens abaixo:</p>
        <table>
            <tr>
                <th>Transação</th>
                <th>Data</th>
                <th>Cód. Operador</th>
                <th>Nome Operador</th>
                <th>Contagem</th>
                <th>Produto</th>
                <th>Código RFID</th>
                <th>Situação RFID</th>
            </tr>
    """

    for item in inconsistencias:
        data_transacao_formatada = item['DT_TRANSACAO'].strftime('%d/%m/%Y %H:%M:%S')
        nome_operador = item.get('NM_OPERADOR', 'N/A')
        situacao_rfid_desc = item.get('DS_SITUACAO_RFID', 'N/A')

        corpo_html += f"""
            <tr>
                <td>{item['NR_TRANSACAO']}</td>
                <td>{data_transacao_formatada}</td>
                <td>{item['CD_OPERADOR']}</td>
                <td>{nome_operador}</td>
                <td>{item['NR_CONTAGEM']}</td>
                <td>{item['CD_PRODUTO']}</td>
                <td>{item['CD_RFID']}</td>
                <td>{situacao_rfid_desc}</td>
            </tr>
        """

    corpo_html += """
        </table>
        <p><b>Ação recomendada:</b> Corrigir a situação dos códigos RFID no sistema para evitar problemas na conferência na filial.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Alerta: RFID com Situação Incorreta em Transação de Saída"
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(EMAIL_TO)
    
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            print(f"E-mail de alerta enviado com sucesso para: {', '.join(EMAIL_TO)}")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")


if __name__ == "__main__":
    # O loop principal não precisa de alterações
    print("Iniciando monitoramento de transações...")
    transacoes_alertadas = set() 
    
    while True:
        try:
            # --- REGISTRA O INÍCIO DA EXECUÇÃO ---
            registrar_log_execucao(CODIGO_ROTINA, STATUS_INICIO)

            # --- REALIZA O TRABALHO PRINCIPAL ---
            resultados = verificar_transacoes()
            
            if resultados:
                novas_inconsistencias = []
                for res in resultados:
                    chave_inconsistencia = (res['NR_TRANSACAO'], res['CD_RFID'])
                    if chave_inconsistencia not in transacoes_alertadas:
                        novas_inconsistencias.append(res)
                        transacoes_alertadas.add(chave_inconsistencia)

                if novas_inconsistencias:
                    print(f"Encontradas {len(novas_inconsistencias)} novas inconsistências. Enviando e-mail...")
                    enviar_email(novas_inconsistencias)
                else:
                    print("Nenhuma nova inconsistência encontrada. Verificação concluída.")
            else:
                print("Nenhuma inconsistência encontrada. Verificação concluída.")
            # REGISTRA O FIM DA EXECUÇÃO ---
            registrar_log_execucao(CODIGO_ROTINA, STATUS_FIM)

            print(f"Ciclo de verificação concluído. Aguardando {INTERVALO_SEGUNDOS} segundos para o próximo...")
            time.sleep(INTERVALO_SEGUNDOS) 
        
        except KeyboardInterrupt:
            print("Monitoramento interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"Ocorreu um erro inesperado no loop principal: {e}")
            time.sleep(300)