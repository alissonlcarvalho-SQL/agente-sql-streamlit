import pyodbc

# Dados da conexão
server = 'snepdtm01v'
database = 'PlanCapWrk'

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    f'SERVER={server};'
    f'DATABASE={database};'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("✅ Conexão bem-sucedida com o SQL Server!")
    conn.close()
except Exception as e:
    print("❌ Erro ao conectar ao SQL Server:")
    print(e)
