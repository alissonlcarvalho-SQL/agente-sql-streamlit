import pyodbc
import re

# Dados da conexão
server = 'snepdtm01v'
database = 'PlanCapWrk'
table = '[PlanCapWrk].[dbo].[CTOP]'

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    f'SERVER={server};'
    f'DATABASE={database};'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)

def obter_colunas(cursor):
    """Obtém os nomes das colunas da tabela."""
    cursor.execute(f"SELECT TOP 1 * FROM {table}")
    return [col[0].lower() for col in cursor.description]

def interpretar_prompt(prompt, colunas):
    """Interpreta o prompt do usuário para gerar uma consulta SQL."""
    prompt = prompt.lower()
    
    # Procura por "top X", "X maiores", "X menores", etc.
    match_top = re.search(r'(\d+)\s+(maiores|menores|principais)', prompt)
    top_n = int(match_top.group(1)) if match_top else 5
    
    coluna_encontrada = None
    for col in colunas:
        if col in prompt:
            coluna_encontrada = col
            break
            
    if "maiores" in prompt:
        ordem = "DESC"
    elif "menores" in prompt:
        ordem = "ASC"
    else:
        ordem = None
        
    sql = f"SELECT TOP {top_n} * FROM {table}"
    
    if coluna_encontrada and ordem:
        sql += f" ORDER BY {coluna_encontrada} {ordem}"
        
    return sql

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    colunas = obter_colunas(cursor)
    
    print("Digite sua pergunta sobre os dados (ex: 'quais os 10 maiores valores?'):")
    prompt = input("> ")
    
    consulta_sql = interpretar_prompt(prompt, colunas)
    
    # --- CORREÇÃO APLICADA AQUI ---
    print(f"""
Consulta gerada:
{consulta_sql}
""")
    
    cursor.execute(consulta_sql)
    resultados = cursor.fetchall()
    
    print("Resultados:")
    for row in resultados:
        print(row)

except Exception as e:
    print(f"Erro ao conectar ou consultar: {e}")