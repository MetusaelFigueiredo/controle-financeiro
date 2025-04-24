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
    "Carro": ["Combustível", "Seguro", "Manutenção", "IPVA", "Bateria"],
    "Consórcio": ["HS"],
    "Energia": ["Conta de Luz"],
    "Mercado": ["Compras Mensais"],
    "Lazer": ["Viagem", "Cinema", "Restaurante", "Streaming", "Beleza"],
    "Saúde": ["Consulta", "Remédio", "Plano de Saúde", "Farmacia"],
    "Despesas Pessoais": ["Salão de Beleza", "Lavanderia", "Cuidados e higiene pessoal", "Farmacia", "Roupas/Sapatos/Acessórios"],
    "Celular/TV/Internet": ["Apple", "Streaming", "Conta de Luz"],
    "Cartão": ["Anuidade", "Juros e Multa"],
    "Viagens": ["Passagem Aéreas"],
    "Alimentação": ["Doces", "Lanche", "Restaurante"],
    "Outros": ["Diversos", "Estacionamento", "IA", "Iphone XR"]
}

mapeamento_personalizado = {
    "Taxa De Anuidade": ("Cartão", "Anuidade"),
    "Juros De Mora - Multa": ("Cartão", "Juros e Multa"),
    "DELICIASDADIR": ("Alimentação", "Doces"),
    "NETFLIX.COM": ("Celular/TV/Internet", "Streaming"),
    "IFD*KEMBERTHY OLIVEI": ("Alimentação", "Lanche"),
    "VARADERO BAR E RESTO": ("Alimentação", "Restaurante"),
    "CONDESSA": ("Despesas Pessoais", "Salão de Beleza"),
    "CAPPTA *UNIQUE ESCOV": ("Despesas Pessoais", "Salão de Beleza"),
    "FORMA CLEAN LAVANDER": ("Despesas Pessoais", "Lavanderia"),
    "56991717Roberta": ("Alimentação", "Lanche"),
    "Amazon Music": ("Celular/TV/Internet", "Streaming"),
    "DELICIASDALUC": ("Alimentação", "Doces"),
    "MP *DELICIASDALUC": ("Alimentação", "Doces"),
    "CONTA VIVO": ("Celular/TV/Internet", "Conta de Luz"),
    "IFD*IFOOD CLUB": ("Alimentação", "Lanche"),
    "ROSBRITHAIRBEAUTY": ("Despesas Pessoais", "Salão de Beleza"),
    "APPLE.COM/BILL": ("Celular/TV/Internet", "Apple"),
    "C M ANDRADE CUNHA LT": ("Alimentação", "Restaurante"),
    "PADARIA AMERICA": ("Alimentação", "Restaurante"),
    "BRAVI PIZZA": ("Alimentação", "Restaurante"),
    "IFD*THATLIN PINHO SI": ("Alimentação", "Lanche"),
    "Cafeliz": ("Alimentação", "Restaurante"),
    "GAMA SUPERMERCADOS": ("Mercado", "Compras Mensais"),
    "MODA MUNDIAL*SHEINC": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "CN SOBREMESAS": ("Alimentação", "Doces"),
    "ANCAR": ("Outros", "Estacionamento"),
    "POSTO CONTI COMIGO": ("Carro", "Combustível"),
    "BISTRO CUIABA": ("Alimentação", "Restaurante"),
    "CleverHenriqueSou": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "HNA*OBOTICARIO": ("Despesas Pessoais", "Cuidados e higiene pessoal"),
    "SHOPEE *XVICTORIASH": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "CAFE JARDINS": ("Alimentação", "Restaurante"),
    "PAGUE MENOS 984": ("Despesas Pessoais", "Farmacia"),
    "FRAZAO BURGUER": ("Alimentação", "Lanche"),
    "FerreiraETaldivo": ("Alimentação", "Lanche"),
    "SUPERMERCADO BIG LAR": ("Mercado", "Compras Mensais"),
    "MERCADO CURIO": ("Mercado", "Compras Mensais"),
    "PG *NP TUNNEL": ("Celular/TV/Internet", "Apple"),
    "BELATTO DELIVERY": ("Alimentação", "Lanche"),
    "SBESOCIEDADE BENEFIC": ("Alimentação", "Lanche"),
    "REDE STOCK": ("Carro", "Combustível"),
    "ESTACAO SCHUTZ": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "VIA VENETO 110": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "SHEIN *SHEIN.COM": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "Propig *EDSON BATER": ("Carro", "Bateria"),
    "GOL LINHAS A*DKDFVV": ("Viagens", "Passagem Aéreas"),
    "DROGASIL 1522": ("Despesas Pessoais", "Farmacia"),
    "DonaAmoraTga": ("Despesas Pessoais", "Roupas/Sapatos/Acessórios"),
    "MIGUELSUTIL": ("Outros", "Diversos"),
    "AUTO CAMPO COMERCIO": ("Outros", "Iphone XR"),
    "EC *ADAPTA": ("Outros", "IA")
}


def categorizar(desc):
    desc = desc.strip()
    for chave in mapeamento_personalizado:
        if chave.lower() in desc.lower():
            return mapeamento_personalizado[chave]
    return ("Outros", "Diversos")

# === ABAS ===
ab_lanc, ab_resumo, ab_painel, ab_importar = st.tabs(["➕ Lançar", "📊 Resumo", "📆 Painel", "📥 Importar Fatura"])

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

with ab_painel:
    st.subheader("📆 Painel Mensal")
    df_painel = st.session_state.dados.copy()
    df_painel["AnoMes"] = df_painel["Data"].dt.to_period("M")
    resumo_mensal = df_painel.groupby(["AnoMes", "Categoria"])["Valor (R$)"].sum().unstack(fill_value=0)

    fig, ax = plt.subplots()
    resumo_mensal.plot(kind="bar", ax=ax)
    ax.set_title("Evolução Mensal")
    ax.set_ylabel("Valor (R$)")
    ax.grid(True)
    st.pyplot(fig)

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

        st.markdown("🔧 Você pode editar as categorias antes de salvar:")
        edited_df = st.data_editor(df_extrato, use_container_width=True, num_rows="dynamic")

        if st.button("Salvar lançamentos importados"):
            edited_df["Parcelas"] = "Única"
            edited_df["Forma de Pagamento"] = "Cartão Crédito"
            edited_df["Status"] = "Pago"
            edited_df["Observações"] = "Importado do extrato Sicredi"
            colunas = ["Data", "Descrição", "Categoria", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas",
                       "Forma de Pagamento", "Status", "Responsável", "Observações"]
            edited_df = edited_df.rename(columns={"Categoria": "Tipo de Despesa"})
            colunas_corrigidas = ["Data", "Descrição", "Tipo de Despesa", "Subcategoria", "Valor (R$)", "Parcelas", "Forma de Pagamento", "Status", "Responsável", "Observações"]
            edited_df = edited_df[colunas_corrigidas]
            st.session_state.dados = pd.concat([st.session_state.dados, edited_df], ignore_index=True)
            set_with_dataframe(aba, st.session_state.dados)
            st.success("Lançamentos importados com sucesso!")
