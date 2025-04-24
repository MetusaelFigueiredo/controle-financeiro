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
    return df

if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

usuario = st.sidebar.selectbox("Entrar como", ["Zael", "Mari"])
st.sidebar.success(f"Você está logado como {usuario}")

subcategorias_opcoes = {
    "Casa": ["Aluguel", "Condomínio", "IPTU", "Manutenção"],
    "Carro": ["Combustível", "Seguro", "Manutenção", "IPVA"],
    "Consórcio": ["HS"],
    "Energia": ["Conta de Luz"],
    "Mercado": ["Compras Mensais", "Extras"],
    "Lazer": ["Viagem", "Cinema", "Restaurante", "Streaming", "Beleza"],
    "Saúde": ["Consulta", "Remédio", "Plano de Saúde"],
    "Outros": ["Diversos"]
}

# === CATEGORIZADOR BÁSICO ===
def categorizar(desc):
    desc = desc.lower()
    if "posto" in desc or "shell" in desc:
        return ("Carro", "Combustível")
    if "netflix" in desc or "amazon" in desc or "stream" in desc:
        return ("Lazer", "Streaming")
    if "supermercado" in desc or "gama" in desc:
        return ("Mercado", "Compras Mensais")
    if "ifood" in desc:
        return ("Lazer", "Restaurante")
    if "padaria" in desc or "cafe" in desc:
        return ("Lazer", "Restaurante")
    if "shein" in desc or "moda" in desc:
        return ("Outros", "Diversos")
    if "vivo" in desc:
        return ("Energia", "Conta de Luz")
    return ("Outros", "Diversos")

# === ABAS ===
ab_lanc, ab_resumo, ab_painel, ab_importar = st.tabs(["➕ Lançar", "📊 Resumo", "📆 Painel", "📥 Importar Fatura"])

with ab_importar:
    st.subheader("📥 Importar Fatura CSV - Sicredi")
    arquivo = st.file_uploader("Escolha o arquivo CSV da fatura", type="csv")

    if arquivo:
        linhas = arquivo.getvalue().decode("utf-8").splitlines()
        transacoes = []
        for linha in linhas:
            partes = linha.strip().split(";")
            if len(partes) >= 6 and "R$" in linha and partes[0].count("/") == 2:
                transacoes.append(partes)

        def parse_valor(valor_str):
            try:
                return -float(valor_str.replace("R$", "").replace("\"", "").strip().replace(".", "").replace(",", "."))
            except:
                return None

        def normalizar_responsavel(nome):
            if "metusael" in nome.lower():
                return "Zael"
            elif "mariana" in nome.lower():
                return "Mari"
            else:
                return "Casal"

        df_raw = pd.DataFrame(transacoes, columns=["Data", "Descrição", "_", "Valor", "__", "___", "Nome"])
        df_raw["Data"] = pd.to_datetime(df_raw["Data"], format="%d/%m/%Y", errors="coerce")
        df_raw["Valor (R$)"] = df_raw["Valor"].apply(parse_valor)
        df_raw["Responsável"] = df_raw["Nome"].apply(normalizar_responsavel)
        df_raw["Descrição"] = df_raw["Descrição"].str.strip()
        df_raw[["Categoria", "Subcategoria"]] = df_raw["Descrição"].apply(lambda x: pd.Series(categorizar(x)))
        df_extrato = df_raw[["Data", "Descrição", "Categoria", "Subcategoria", "Valor (R$)", "Responsável"]].dropna()

        st.dataframe(df_extrato, use_container_width=True)

        if st.button("Salvar lançamentos importados"):
            df_extrato["Parcelas"] = "Única"
            df_extrato["Forma de Pagamento"] = "Cartão Crédito"
            df_extrato["Status"] = "Pago"
            df_extrato["Observações"] = "Importado do extrato Sicredi"
            colunas = ["Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                       "Forma de Pagamento", "Status", "Responsável", "Observações"]
            df_extrato = df_extrato.rename(columns={"Categoria": "Tipo de Despesa"})
            df_extrato = df_extrato[colunas]
            st.session_state.dados = pd.concat([st.session_state.dados, df_extrato], ignore_index=True)
            set_with_dataframe(aba, st.session_state.dados)
            st.success("Lançamentos importados com sucesso!")
