import pyodbc

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

# Função para interpretar prompt simples
def interpretar_prompt(prompt):
    prompt = prompt.lower()
    sql = f"SELECT TOP 5 * FROM {table}"

    if "maiores" in prompt:
        sql += " ORDER BY valor DESC"
    elif "menores" in prompt:
        sql += " ORDER BY valor ASC"

    return sql

# Executa a consulta
try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    print("Digite sua pergunta sobre os dados:")
    prompt = input("> ")

    consulta_sql = interpretar_prompt(prompt)
    
    # --- CORREÇÃO APLICADA AQUI ---
    print(f"""Consulta gerada:
{consulta_sql}
""")

    cursor.execute(consulta_sql)
    resultados = cursor.fetchall()

    print("Resultados:")
    for row in resultados:
        print(row)

except Exception as e:
    print("Erro ao conectar ou consultar: " + str(e))