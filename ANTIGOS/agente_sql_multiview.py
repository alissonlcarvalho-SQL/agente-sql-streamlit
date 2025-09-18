import pyodbc
import re
import pandas as pd
import logging
from datetime import datetime

# Configuração de log
logging.basicConfig(filename='agente_sql_multiview.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

server = 'snepdtm01v'
database = 'PlanCapWrk'

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    f'SERVER={server};'
    f'DATABASE={database};'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)

def listar_views_e_tabelas(cursor):
    """Lista todas as Views e Tabelas (do tipo 'BASE TABLE') disponíveis no schema 'dbo'."""
    cursor.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = 'dbo'
        UNION ALL
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'dbo'
    """)
    return sorted([row[0] for row in cursor.fetchall()])

def obter_colunas(cursor, nome_objeto):
    """Obtém as colunas de uma tabela ou view específica."""
    cursor.execute(f"SELECT TOP 1 * FROM [{database}].[dbo].[{nome_objeto}]")
    return [col[0].lower() for col in cursor.description]

def interpretar_prompt(prompt, nome_objeto, colunas):
    """Interpreta o prompt do usuário para gerar uma consulta SQL."""
    prompt_lower = prompt.lower()
    
    match_top = re.search(r'(\d+)', prompt_lower)
    top_n = int(match_top.group(1)) if match_top else 50 # Default para 50

    clausula_order_by = ""
    # --- CORREÇÃO APLICADA AQUI ---
    # A lógica agora aceita "na coluna" ou "da coluna"
    match_ordem = re.search(r'(maiores|menores)\s+(?:valores|registros)?\s*(?:(?:na|da)\s+coluna)?\s+(\w+)', prompt_lower)
    
    if match_ordem:
        direcao = "DESC" if match_ordem.group(1) == "maiores" else "ASC"
        coluna_ordem = match_ordem.group(2)
        
        if coluna_ordem in colunas:
            # Verifica se a coluna precisa ser convertida para um tipo numérico para ordenação
            # Adicione outras colunas que são texto mas representam números aqui
            if coluna_ordem in ['hp', 'sv_client_unit_count']: # Exemplo, caso sv_client_unit_count seja texto
                clausula_order_by = f" ORDER BY CAST([{coluna_ordem}] AS INT) {direcao}"
            else:
                clausula_order_by = f" ORDER BY [{coluna_ordem}] {direcao}"

    filtros = []
    prompt_filtros = prompt_lower.replace("traga apenas o que for", "=").replace(",", " ")
    
    padrao_filtro = re.compile(r"(\w+)\s*=\s*(\w+)")
    matches = padrao_filtro.findall(prompt_filtros)
    
    for coluna, valor in matches:
        if coluna in colunas:
            # Verifica se o valor é numérico ou texto para formatar a consulta corretamente
            if valor.isnumeric():
                 filtros.append(f"[{coluna}] = {valor}")
            else:
                 filtros.append(f"[{coluna}] = '{valor.upper()}'")


    sql = f"SELECT TOP {top_n} * FROM [{database}].[dbo].[{nome_objeto}]"
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    if clausula_order_by:
        sql += clausula_order_by

    return sql

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    objetos_consultaveis = listar_views_e_tabelas(cursor)
    print("Tabelas e Views disponíveis:")
    for obj in objetos_consultaveis:
        print("-", obj)
    
    print()
    print("Digite o nome da tabela ou view que deseja consultar:")
    objeto_selecionado = input("> ")
    if objeto_selecionado not in objetos_consultaveis:
        print("Objeto não encontrado.")
    else:
        colunas = obter_colunas(cursor, objeto_selecionado)
        print("Digite sua pergunta sobre os dados:")
        prompt = input("> ")
        consulta_sql = interpretar_prompt(prompt, objeto_selecionado, colunas)
        logging.info(f"Consulta gerada: {consulta_sql}")

        print("\n---")
        print(f"Consulta gerada:\n{consulta_sql}")
        print("---\n")
        
        cursor.execute(consulta_sql)
        resultados = cursor.fetchall()
        colunas_resultado = [desc[0] for desc in cursor.description]

        print("Resultados:")
        for row in resultados:
            print(row)

        if resultados:
            df = pd.DataFrame.from_records(resultados, columns=colunas_resultado)
            nome_arquivo = f"resultado_{objeto_selecionado}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            
            print()
            print(f"Resultados exportados para: {nome_arquivo}")
        else:
            print("A consulta não retornou resultados.")

except Exception as e:
    logging.error(f"Erro: {e}")
    print("Erro ao conectar ou consultar:", e)