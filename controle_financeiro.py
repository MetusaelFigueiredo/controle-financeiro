import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Controle Financeiro", layout="wide")
st.title("📊 Controle Financeiro Pessoal")

CAMINHO_ARQUIVO = "dados_financeiros.csv"

# Tenta carregar dados do arquivo
if "dados" not in st.session_state:
    if os.path.exists(CAMINHO_ARQUIVO):
        st.session_state.dados = pd.read_csv(CAMINHO_ARQUIVO)
    else:
        st.session_state.dados = pd.DataFrame(columns=[
            "Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
            "Forma de Pagamento", "Status", "Responsável", "Observações"
        ])

# Garantir que a coluna "Data" esteja em datetime64[ns]
st.session_state.dados["Data"] = pd.to_datetime(st.session_state.dados["Data"], errors='coerce')

# Mapeamento de subcategorias por tipo de despesa
subcategorias_opcoes = {
    "Casa": ["Aluguel", "Condomínio", "IPTU", "Manutenção"],
    "Carro": ["Combustível", "Seguro", "Manutenção", "IPVA"],
    "Consórcio": ["HS"],
    "Energia": ["Conta de Luz"],
    "Mercado": ["Compras Mensais", "Extras"],
    "Lazer": ["Viagem", "Cinema", "Restaurante", "Beleza"],
    "Saúde": ["Consulta", "Remédio", "Plano de Saúde"],
    "Outros": ["Diversos"]
}

# Formulário
st.subheader("📌 Novo Lançamento")
col1, col2, col3 = st.columns(3)
data = pd.to_datetime(col1.date_input("Data", value=date.today()))
descricao = col2.text_input("Descrição")
categoria = col3.selectbox("Categoria", ["Receita", "Despesa"])

valor = st.number_input("Valor (R$)", step=0.01)
parcelas = st.text_input("Parcelas (ex: 1/3 ou Única)", value="Única")
pagamento = st.selectbox("Forma de Pagamento", ["Transferência", "Cartão Crédito", "Boleto", "Pix", "Dinheiro"])
status = st.selectbox("Status", ["Pago", "A Pagar", "Futuro"])
responsavel = st.selectbox("Responsável", ["Zael", "Mari", "Casal"])

# Campos dinâmicos
tipo_despesa = "—"
subcategoria = "—"
if categoria == "Despesa":
    tipo_despesa = st.selectbox("Tipo de Despesa", list(subcategorias_opcoes.keys()))
    subcategoria = st.selectbox("Subcategoria", subcategorias_opcoes[tipo_despesa])

obs = st.text_area("Observações")

# Botão de envio
if st.button("Adicionar Lançamento"):
    novo = pd.DataFrame([[data, descricao, categoria, tipo_despesa, subcategoria, valor, parcelas,
                          pagamento, status, responsavel, obs]],
                        columns=[
                            "Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                            "Forma de Pagamento", "Status", "Responsável", "Observações"
                        ])
    st.session_state.dados = pd.concat([st.session_state.dados, novo], ignore_index=True)
    st.session_state.dados.to_csv(CAMINHO_ARQUIVO, index=False)
    st.success("Lançamento adicionado com sucesso!")

# Exibir tabela
st.subheader("📄 Lançamentos")
st.dataframe(st.session_state.dados, use_container_width=True)

# Aviso de data inválida
if st.session_state.dados["Data"].isnull().any():
    st.warning("⚠️ Existem lançamentos com data inválida.")

# === RESUMO FINANCEIRO COM FILTROS ===
st.subheader("📊 Resumo Financeiro")

# Filtros
with st.expander("🔎 Filtros"):
    col1, col2, col3 = st.columns(3)
    filtro_responsavel = col1.selectbox("Filtrar por Responsável", ["Todos"] + sorted(st.session_state.dados["Responsável"].dropna().unique()))
    filtro_tipo = col2.selectbox("Filtrar por Tipo de Despesa", ["Todos"] + sorted(st.session_state.dados["Tipo de Despesa"].dropna().unique()))
    filtro_mes = col3.selectbox("Filtrar por Mês", ["Todos"] + sorted(st.session_state.dados["Data"].dropna().dt.to_period("M").astype(str).unique()))

# Aplicar filtros
df_filtrado = st.session_state.dados.copy()

if filtro_responsavel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Responsável"] == filtro_responsavel]
if filtro_tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Tipo de Despesa"] == filtro_tipo]
if filtro_mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Data"].dt.to_period("M").astype(str) == filtro_mes]

# Cálculos
total_receitas = df_filtrado[df_filtrado["Categoria"] == "Receita"]["Valor (R$)"].sum()
total_despesas = df_filtrado[df_filtrado["Categoria"] == "Despesa"]["Valor (R$)"].sum()
saldo = total_receitas + total_despesas

# Exibir resumo
col1, col2, col3 = st.columns(3)
col1.metric("Receitas", f"R$ {total_receitas:,.2f}")
col2.metric("Despesas", f"R$ {abs(total_despesas):,.2f}")
col3.metric("Saldo", f"R$ {saldo:,.2f}")
