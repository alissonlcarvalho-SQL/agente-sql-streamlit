import streamlit as st
import pyodbc
import pandas as pd
from datetime import datetime
import io

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Agente de Consulta SQL")

# --- LÓGICA DE LOGIN ---
def check_password():
    """Retorna True se a senha estiver correta, False caso contrário."""
    if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
    else:
        st.session_state["password_correct"] = False
        st.error("😕 Senha incorreta. Por favor, tente novamente.")

# --- INÍCIO DA INTERFACE ---

# Se a senha ainda não foi validada, mostra o campo para inserção
if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.title("🔒 Agente de Consulta SQL")
    st.markdown("Por favor, insira a senha para acessar a aplicação.")
    st.text_input("Senha", type="password", on_change=check_password, key="password")

# Se a senha estiver correta, mostra a aplicação completa
else:
    # --- APLICAÇÃO PRINCIPAL COMEÇA AQUI ---

    st.title("🤖 Agente de Consulta SQL Interativo")
    st.markdown("Crie e execute consultas no banco de dados de forma visual e intuitiva.")

    # --- Lógica de Cache e Conexão com o Banco ---
    @st.cache_resource
    def conectar_banco():
        """Cria e retorna a conexão com o banco de dados."""
        try:
            server = 'snepdtm01v'
            database = 'PlanCapWrk'
            conn_str = (
                'DRIVER={ODBC Driver 18 for SQL Server};'
                f'SERVER={server};'
                f'DATABASE={database};'
                'Trusted_Connection=yes;'
                'TrustServerCertificate=yes;'
            )
            conn = pyodbc.connect(conn_str)
            return conn
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return None

    @st.cache_data
    def listar_tabelas(_cursor):
        """Lista todas as Tabelas (do tipo 'BASE TABLE') disponíveis no schema 'dbo'."""
        _cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'dbo'
        """)
        return sorted([row[0] for row in _cursor.fetchall()])

    @st.cache_data
    def listar_views(_cursor):
        """Lista todas as Views disponíveis no schema 'dbo'."""
        _cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS 
            WHERE TABLE_SCHEMA = 'dbo'
        """)
        return sorted([row[0] for row in _cursor.fetchall()])

    @st.cache_data
    def obter_colunas(_cursor, nome_objeto):
        """Obtém as colunas de uma tabela ou view específica."""
        _cursor.execute(f"SELECT TOP 1 * FROM [PlanCapWrk].[dbo].[{nome_objeto}]")
        return [col[0] for col in _cursor.description]

    # --- Função para Montar a Query ---
    def montar_query(objeto, top_n, tipo_ordem, coluna_ordem, filtros):
        """Monta a string da consulta SQL com base nas seleções do formulário."""
        direcao = "DESC" if tipo_ordem == "Maiores Valores" else "ASC"
        if coluna_ordem in ['hp', 'sv_client_unit_count']:
            clausula_order_by = f" ORDER BY CAST([{coluna_ordem}] AS INT) {direcao}"
        else:
            clausula_order_by = f" ORDER BY [{coluna_ordem}] {direcao}"
        
        clausula_where = ""
        if filtros:
            condicoes = []
            for f in filtros:
                valor_formatado = f"'{f['valor'].upper()}'" if not f['valor'].isnumeric() else f['valor']
                condicoes.append(f"[{f['coluna']}] = {valor_formatado}")
            clausula_where = " WHERE " + " AND ".join(condicoes)

        query = f"SELECT TOP {top_n} * FROM [PlanCapWrk].[dbo].[{objeto}]{clausula_where}{clausula_order_by}"
        return query

    # --- Lógica Principal da Interface ---
    conn = conectar_banco()
    if conn:
        cursor = conn.cursor()
        st.success("Conexão com o banco de dados estabelecida com sucesso!")
        st.divider()

        st.markdown("### 1. Escolha a Fonte dos Dados")
        tipo_objeto = st.radio(
            "Você deseja consultar uma Tabela ou uma View?",
            ("Tabela", "View"),
            horizontal=True,
            label_visibility="collapsed"
        )

        objeto_selecionado = None
        if tipo_objeto == "Tabela":
            lista_tabelas = listar_tabelas(cursor)
            objeto_selecionado = st.selectbox("Selecione a Tabela:", options=lista_tabelas, index=None, placeholder="Selecione uma tabela...")
        elif tipo_objeto == "View":
            lista_views = listar_views(cursor)
            objeto_selecionado = st.selectbox("Selecione a View:", options=lista_views, index=None, placeholder="Selecione uma view...")
        
        if objeto_selecionado:
            colunas = obter_colunas(cursor, objeto_selecionado)
            
            st.markdown("### 2. Defina a Ordenação e Quantidade")
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_ordem = st.radio("Ordenar por:", ("Maiores Valores", "Menores Valores"), horizontal=True)
            with col2:
                coluna_ordem = st.selectbox("Coluna para ordenar:", options=colunas)
            with col3:
                top_n = st.number_input("Quantidade de registros:", min_value=1, value=50)

            st.divider()
            
            st.markdown("### 3. Adicione Filtros (Cláusula WHERE)")
            
            if 'filtros' not in st.session_state:
                st.session_state.filtros = []

            with st.container(border=True):
                f_col1, f_col2, f_col3 = st.columns([3, 2, 1])
                with f_col1:
                    coluna_filtro = st.selectbox("Coluna", options=colunas, key="col_filtro_novo")
                with f_col2:
                    valor_filtro = st.text_input("Valor", key="val_filtro_novo")
                with f_col3:
                    st.markdown("##")
                    if st.button("Adicionar Filtro"):
                        if valor_filtro:
                            st.session_state.filtros.append({"coluna": coluna_filtro, "valor": valor_filtro})
                            st.rerun()
                        else:
                            st.warning("O valor do filtro não pode ser vazio.")
            
            if st.session_state.filtros:
                st.markdown("**Filtros Ativos:**")
                for i, filtro in enumerate(st.session_state.filtros):
                    r_col1, r_col2 = st.columns([5, 1])
                    with r_col1:
                        st.info(f"`{filtro['coluna']}` = `{filtro['valor']}`")
                    with r_col2:
                        if st.button(f"Remover", key=f"remover_{i}"):
                            st.session_state.filtros.pop(i)
                            st.rerun()

            st.divider()
            
            if st.button("🚀 Executar Consulta", type="primary", use_container_width=True):
                query = montar_query(objeto_selecionado, top_n, tipo_ordem, coluna_ordem, st.session_state.filtros)
                
                with st.spinner("Executando consulta no banco..."):
                    try:
                        st.markdown("#### Consulta SQL Gerada:")
                        st.code(query, language="sql")
                        
                        cursor.execute(query)
                        resultados = cursor.fetchall()
                        colunas_resultado = [desc[0] for desc in cursor.description]
                        
                        if resultados:
                            df = pd.DataFrame.from_records(resultados, columns=colunas_resultado)
                            st.markdown("#### Resultados:")
                            st.dataframe(df)
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False, sheet_name='Resultados')
                            
                            excel_bytes = output.getvalue()
                            nome_arquivo = f"resultado_{objeto_selecionado}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            
                            st.download_button(
                                label="📥 Baixar Resultados em Excel",
                                data=excel_bytes,
                                file_name=nome_arquivo,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.warning("A consulta não retornou resultados.")
                            
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao executar a consulta: {e}")
    else:
        st.error("Não foi possível conectar ao banco de dados. Verifique as configurações e a conexão de rede.")