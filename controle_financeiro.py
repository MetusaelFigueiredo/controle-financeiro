import streamlit as st
import pandas as pd
from datetime import date
import os
import json

import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Controle Financeiro", layout="wide")
st.title("📊 Financeiro Pessoal")

@st.cache_resource
def autenticar_google():
    escopo = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"], escopo)
    cliente = gspread.authorize(credenciais)
    return cliente

cliente = autenticar_google()

@st.cache_resource
def carregar_planilha():
    planilha = cliente.open("Controle Financeiro")
    return planilha.sheet1

aba = carregar_planilha()

@st.cache_data(ttl=300)
def carregar_dados():
    df = get_as_dataframe(aba)
    df = df.dropna(how="all")
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
    df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce")
    df.loc[df["Categoria"] == "Despesa", "Valor (R$)"] *= -1
    df.loc[df["Categoria"].isna() & (df["Tipo de Despesa"] != "—"), "Categoria"] = "Despesa"
    df.loc[df["Categoria"].isna() & (df["Tipo de Despesa"] == "—"), "Categoria"] = "Receita"
    return df

if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

usuario = st.sidebar.selectbox("Entrar como", ["Zael", "Mari"])
st.sidebar.success(f"Você está logado como {usuario}")

# As variáveis subcategorias_opcoes e mapeamento_personalizado devem ser mantidas aqui como no código original

# === ABAS ===
ab_lanc, ab_resumo, ab_painel, ab_importar = st.tabs(["➕ Lançar", "📊 Resumo", "🗖️ Painel", "📥 Importar Fatura"])

with ab_lanc:
    st.subheader("➕ Novo Lançamento")
    col1, col2, col3 = st.columns(3)
    data = col1.date_input("Data", value=date.today())
    descricao = col2.text_input("Descrição")
    categoria = col3.selectbox("Categoria", ["Receita", "Despesa"])

    valor = st.number_input("Valor (R$)", step=0.01)
    parcelas = st.text_input("Parcelas", value="Única")
    pagamento = st.selectbox("Forma de Pagamento", ["Transferência", "Cartão Crédito", "Boleto", "Pix", "Dinheiro"])
    status = st.selectbox("Status", ["Pago", "A Pagar", "Futuro"])
    responsavel = st.selectbox("Responsável", ["Zael", "Mari", "Casal"])

    tipo_despesa = subcategoria = "—"
    if categoria == "Despesa":
        tipo_despesa = st.selectbox("Tipo de Despesa", list(subcategorias_opcoes.keys()))
        subcategoria = st.selectbox("Subcategoria", subcategorias_opcoes[tipo_despesa])

    obs = st.text_area("Observações")

    if st.button("Salvar Lançamento"):
        novo = pd.DataFrame([[data, descricao, categoria, tipo_despesa, subcategoria, valor, parcelas,
                              pagamento, status, responsavel, obs]],
                             columns=["Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                                      "Forma de Pagamento", "Status", "Responsável", "Observações"])
        st.session_state.dados = pd.concat([st.session_state.dados, novo], ignore_index=True)
        set_with_dataframe(aba, st.session_state.dados)
        st.session_state.dados = carregar_dados()
        st.success("Lançamento salvo com sucesso!")

with ab_resumo:
    st.subheader("📊 Resumo Financeiro")
    st.session_state.dados = carregar_dados()  # ⚠️ Força a recarga mais atual da base

    col1, col2, col3 = st.columns(3)
    filtro_resp = col1.selectbox("Responsável", ["Todos"] + sorted(st.session_state.dados["Responsável"].dropna().unique()))
    filtro_tipo = col2.selectbox("Tipo de Despesa", ["Todos"] + sorted(st.session_state.dados["Tipo de Despesa"].dropna().unique()))
    filtro_mes = col3.selectbox("Mês", ["Todos"] + sorted(st.session_state.dados["Data"].dropna().dt.to_period("M").astype(str).unique()))

    df_f = st.session_state.dados.copy()
    if filtro_resp != "Todos":
        df_f = df_f[df_f["Responsável"] == filtro_resp]
    if filtro_tipo != "Todos":
        df_f = df_f[df_f["Tipo de Despesa"] == filtro_tipo]
    if filtro_mes != "Todos":
        df_f = df_f[df_f["Data"].dt.to_period("M").astype(str) == filtro_mes]

    receitas = df_f[df_f["Categoria"] == "Receita"]["Valor (R$)"].sum()
    despesas = df_f[df_f["Categoria"] == "Despesa"]["Valor (R$)"].sum()
    saldo = receitas + despesas

    col1.metric("Receitas", f"R$ {receitas:,.2f}")
    col2.metric("Despesas", f"R$ {abs(despesas):,.2f}")
    col3.metric("Saldo", f"R$ {saldo:,.2f}")
