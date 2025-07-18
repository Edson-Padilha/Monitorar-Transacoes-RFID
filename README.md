# Monitor de Inconsistências de RFID em Transações

Este projeto consiste em um script de monitoramento em Python que se conecta a um banco de dados Oracle para identificar e alertar sobre inconsistências em transações de saída de mercadorias.

## 🎯 Objetivo

O principal objetivo deste script é resolver um problema operacional crítico: o envio de produtos com códigos RFID em situações incorretas (ex: "Em Contagem", "Encerrado") para filiais. Tais inconsistências causam transtornos durante a conferência no recebimento, exigindo processos manuais de devolução e correção.

Este monitoramento atua de forma proativa, verificando continuamente as transações e disparando um e-mail de alerta para os responsáveis assim que uma inconsistência é detectada, permitindo que a correção seja feita antes do envio da mercadoria.

## ✨ Funcionalidades Principais

* **Monitoramento Contínuo:** O script roda em um loop contínuo, verificando o banco de dados em intervalos de tempo configuráveis.
* **Regras de Negócio Específicas:** A consulta SQL é construída para identificar precisamente as transações que atendem aos critérios de inconsistência.
* **Alertas por E-mail:** Envia notificações de e-mail formatadas em HTML, contendo todos os detalhes relevantes para uma ação rápida.
* **Informações Detalhadas:** O alerta inclui dados da transação, data, operador (código e nome), produto, contagem e o código RFID específico com sua situação.
* **Gerenciamento Seguro de Credenciais:** Utiliza um arquivo `.env` para armazenar senhas e dados sensíveis de conexão, mantendo-os fora do código-fonte.
* **Evita Alertas Duplicados:** O script controla os alertas já enviados para não notificar repetidamente sobre a mesma inconsistência durante sua execução.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Banco de Dados:** Oracle
* **Bibliotecas Python:**
    * `cx_Oracle`: Para a conexão com o banco de dados Oracle.
    * `python-dotenv`: Para carregar as variáveis de ambiente do arquivo `.env`.

## 🚀 Como Usar

Siga os passos abaixo para configurar e executar o monitoramento.

### 1. Pré-requisitos

* **Python 3.x** instalado na máquina.
* **Oracle Instant Client** instalado e com seu caminho (`lib_dir`) acessível pelo sistema. O `cx_Oracle` depende dele para funcionar.

### 2. Instalação

1.  **Clone ou baixe este projeto** para um diretório em sua máquina.

2.  **Crie um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Crie o arquivo `requirements.txt`** com o seguinte conteúdo:
    ```
    cx_Oracle==8.3.0
    python-dotenv==0.21.0
    ```

4.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuração (Arquivo .env)

Na raiz do projeto, crie um arquivo chamado `.env`. Este arquivo guardará todas as suas credenciais de forma segura. Preencha-o com as suas informações, seguindo o modelo abaixo:

```
# Credenciais do Banco de Dados Oracle
DB_USER=seu_usuario_oracle
DB_PASSWORD=sua_senha_oracle
DB_DSN=seu_host:porta/seu_service_name

# Configurações do Servidor de E-mail (SMTP)
EMAIL_HOST=smtp.seu-provedor.com
EMAIL_PORT=587
EMAIL_USER=seu_email@provedor.com
EMAIL_PASSWORD=sua_senha_de_app_ou_normal
EMAIL_FROM=seu_email_remetente@provedor.com

# Lista de E-mails para receber o alerta (separados por vírgula)
EMAIL_TO=destinatario1@email.com,destinatario2@email.com,destinatario3@email.com
```

### 4. Execução

Com o ambiente virtual ativado e o arquivo `.env` configurado, execute o script principal:

```bash
python monitor_transacoes.py
```

O terminal exibirá mensagens de status, informando quando as verificações são feitas e se alguma inconsistência foi encontrada e notificada. Para parar a execução, pressione `Ctrl+C`.

---

## 🔍 Consulta SQL Utilizada

A lógica central do monitoramento reside na consulta SQL. A versão final e otimizada está abaixo:

<details>
<summary><strong>Clique para expandir e ver a consulta SQL</strong></summary>

```sql
SELECT
    t.nr_transacao,
    t.dt_transacao,
    t.dt_cadastro,
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
    AND pcr.tp_situacao <> 1
    -- O filtro de data pode ser ajustado conforme a necessidade
    AND t.dt_transacao > TO_DATE('****', 'DD/MM/YYYY')
ORDER BY
    t.nr_transacao, pcr.cd_rfid
```

</details>