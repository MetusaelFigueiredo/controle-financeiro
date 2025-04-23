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
st.title("📊 Financeiro Pessoal")

# === AUTENTICAÇÃO COM GOOGLE SHEETS ===
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

# === LER OS DADOS DA PLANILHA ===
@st.cache_data(ttl=300)
def carregar_dados():
    df = get_as_dataframe(aba)
    df = df.dropna(how="all")
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
    df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce")
    df.loc[df["Categoria"] == "Despesa", "Valor (R$)"] *= -1
    return df

if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

subcategorias_opcoes = {
    "Casa": ["Aluguel", "Condomínio", "IPTU", "Manutenção"],
    "Carro": ["Combustível", "Seguro", "Manutenção", "IPVA"],
    "Consórcio": ["HS"],
    "Igreja": ["Dízimo", "Ofertas","Missões"],
    "Energia": ["Conta de Luz"],
    "Mercado": ["Compras Mensais", "Extras"],
    "Lazer": ["Viagem", "Cinema", "Restaurante", "Beleza"],
    "Saúde": ["Consulta", "Remédio", "Plano de Saúde"],
    "Outros": ["Diversos"]
}

# === ABAS ===
ab_lanc, ab_resumo, ab_painel = st.tabs(["➕ Lançar", "📊 Resumo", "📆 Painel"])

with ab_lanc:
    st.subheader("➕ Novo")
    col1, col2 = st.columns(2)
    data = pd.to_datetime(col1.date_input("Data", value=date.today()))
    descricao = col2.text_input("Descrição")

    categoria = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
    valor = st.number_input("Valor", step=0.01)

    col3, col4 = st.columns(2)
    parcelas = col3.text_input("Parcelas", value="Única")
    pagamento = col4.selectbox("Pagamento", ["Transferência", "Cartão Crédito", "Boleto", "Pix", "Dinheiro"])

    status = st.selectbox("Status", ["Pago", "A Pagar", "Futuro"])
    responsavel = st.selectbox("Responsável", ["Zael", "Mari", "Casal"])

    tipo_despesa = "—"
    subcategoria = "—"
    if categoria == "Despesa":
        tipo_despesa = st.selectbox("Despesa", list(subcategorias_opcoes.keys()))
        subcategoria = st.selectbox("Subcategoria", subcategorias_opcoes[tipo_despesa])

    obs = st.text_area("Obs")

    if st.button("Salvar"):
        if descricao.strip() == "" or valor == 0:
            st.warning("Preencha a descrição e o valor.")
        else:
            valor_final = -valor if categoria == "Despesa" else valor
            novo = pd.DataFrame([[data, descricao, categoria, tipo_despesa, subcategoria, valor_final, parcelas,
                                  pagamento, status, responsavel, obs]],
                                columns=[
                                    "Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                                    "Forma de Pagamento", "Status", "Responsável", "Observações"
                                ])
            st.session_state.dados = pd.concat([st.session_state.dados, novo], ignore_index=True)
            set_with_dataframe(aba, st.session_state.dados)
            st.success("Lançado com sucesso!")

with ab_resumo:
    st.subheader("📊 Resumo")
    if not st.session_state.dados.empty:
        col1, col2, col3 = st.columns(3)
        filtro_responsavel = col1.selectbox("Responsável", ["Todos"] + sorted(st.session_state.dados["Responsável"].dropna().unique()))
        filtro_tipo = col2.selectbox("Tipo de Despesa", ["Todos"] + sorted(st.session_state.dados["Tipo de Despesa"].dropna().unique()))
        filtro_mes = col3.selectbox("Mês", ["Todos"] + sorted(st.session_state.dados["Data"].dropna().dt.to_period("M").astype(str).unique()))

        df_filtrado = st.session_state.dados.copy()
        if filtro_responsavel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Responsável"] == filtro_responsavel]
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo de Despesa"] == filtro_tipo]
        if filtro_mes != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Data"].dt.to_period("M").astype(str) == filtro_mes]

        total_receitas = df_filtrado[df_filtrado["Categoria"] == "Receita"]["Valor (R$)"].sum()
        total_despesas = df_filtrado[df_filtrado["Categoria"] == "Despesa"]["Valor (R$)"].sum()
        saldo = total_receitas + total_despesas

        c1, c2, c3 = st.columns(3)
        c1.metric("Receita", f"R$ {total_receitas:,.2f}")
        c2.metric("Despesa", f"R$ {abs(total_despesas):,.2f}")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")

        st.divider()
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado.")

with ab_painel:
    st.subheader("📆 Painel")
    if not st.session_state.dados.empty:
        df_painel = st.session_state.dados.copy()
        df_painel["AnoMes"] = df_painel["Data"].dt.to_period("M")
        resumo = df_painel.groupby(["AnoMes", "Categoria"])["Valor (R$)"].sum().unstack().fillna(0)
        resumo["Saldo"] = resumo.sum(axis=1)

        st.dataframe(resumo, use_container_width=True)

        if st.checkbox("Mostrar gráfico", value=True):
            fig, ax = plt.subplots()
            resumo.plot(kind="bar", stacked=False, ax=ax)
            ax.set_title("Evolução Mensal")
            ax.set_ylabel("R$")
            st.pyplot(fig)
    else:
        st.info("Sem dados para exibir o painel.")
