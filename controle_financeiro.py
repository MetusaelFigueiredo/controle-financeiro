import streamlit as st
import pandas as pd
from datetime import date
import os
import json

import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt

st.set_page_config(page_title="Controle Financeiro", layout="wide")
st.title("📊 Controle Financeiro Pessoal")

# === AUTENTICAÇÃO COM GOOGLE SHEETS ===
def autenticar_google():
    escopo = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"], escopo)
    cliente = gspread.authorize(credenciais)
    return cliente

cliente = autenticar_google()
planilha = cliente.open("Controle Financeiro")
aba = planilha.sheet1

# === LER OS DADOS DA PLANILHA ===
if "dados" not in st.session_state:
    df = get_as_dataframe(aba)
    df = df.dropna(how="all")
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
    df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce")
    df.loc[df["Categoria"] == "Despesa", "Valor (R$)"] *= -1
    st.session_state.dados = df

# === MAPEAMENTO DE SUBCATEGORIAS ===
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

# === FORMULÁRIO ===
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

tipo_despesa = "—"
subcategoria = "—"
if categoria == "Despesa":
    tipo_despesa = st.selectbox("Tipo de Despesa", list(subcategorias_opcoes.keys()))
    subcategoria = st.selectbox("Subcategoria", subcategorias_opcoes[tipo_despesa])

obs = st.text_area("Observações")

# === SALVAR NA PLANILHA ===
if st.button("Adicionar Lançamento"):
    valor_final = -valor if categoria == "Despesa" else valor
    novo = pd.DataFrame([[data, descricao, categoria, tipo_despesa, subcategoria, valor_final, parcelas,
                          pagamento, status, responsavel, obs]],
                        columns=[
                            "Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                            "Forma de Pagamento", "Status", "Responsável", "Observações"
                        ])
    st.session_state.dados = pd.concat([st.session_state.dados, novo], ignore_index=True)
    set_with_dataframe(aba, st.session_state.dados)
    st.success("Lançamento adicionado com sucesso!")

# === TABELA DE LANÇAMENTOS ===
st.subheader("📄 Lançamentos")
st.dataframe(st.session_state.dados, use_container_width=True)

# === RESUMO FINANCEIRO COM FILTROS ===
st.subheader("📊 Resumo Financeiro")

with st.expander("🔎 Filtros"):
    col1, col2, col3 = st.columns(3)
    filtro_responsavel = col1.selectbox("Filtrar por Responsável", ["Todos"] + sorted(st.session_state.dados["Responsável"].dropna().unique()))
    filtro_tipo = col2.selectbox("Filtrar por Tipo de Despesa", ["Todos"] + sorted(st.session_state.dados["Tipo de Despesa"].dropna().unique()))
    filtro_mes = col3.selectbox("Filtrar por Mês", ["Todos"] + sorted(st.session_state.dados["Data"].dropna().dt.to_period("M").astype(str).unique()))

df_filtrado = st.session_state.dados.copy()
if filtro_responsavel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Responsável"] == filtro_responsavel]
if filtro_tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Tipo de Despesa"] == filtro_tipo]
if filtro_mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Data"].dt.to_period("M").astype(str) == filtro_mes]

# === CÁLCULOS E MÉTRICAS ===
total_receitas = df_filtrado[df_filtrado["Categoria"] == "Receita"]["Valor (R$)"].sum()
total_despesas = df_filtrado[df_filtrado["Categoria"] == "Despesa"]["Valor (R$)"].sum()
saldo = total_receitas + total_despesas

col1, col2, col3 = st.columns(3)
col1.metric("Receitas", f"R$ {total_receitas:,.2f}")
col2.metric("Despesas", f"R$ {abs(total_despesas):,.2f}")
col3.metric("Saldo", f"R$ {saldo:,.2f}")

# === 📆 PAINEL MENSAL ===
st.subheader("📆 Painel Mensal")

df_painel = st.session_state.dados.copy()
df_painel["AnoMes"] = df_painel["Data"].dt.to_period("M")
resumo = df_painel.groupby(["AnoMes", "Categoria"])["Valor (R$)"].sum().unstack().fillna(0)
resumo["Saldo"] = resumo.sum(axis=1)

st.dataframe(resumo, use_container_width=True)

fig, ax = plt.subplots()
resumo.plot(kind="bar", stacked=False, ax=ax)
ax.set_title("Evolução Mensal")
ax.set_ylabel("R$")
st.pyplot(fig)
