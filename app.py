"""Controle de estoque da farmácia (Streamlit + Google Sheets).
Rodar: streamlit run app.py"""
import base64
import html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from PIL import Image

import estoque as e

PASTA = Path(__file__).parent
LOGO = PASTA / "assets" / "logo.png"
FUSO = ZoneInfo("America/Recife")

st.set_page_config(
    page_title="Controle de Estoque - Farmácia Descontão",
    page_icon=Image.open(LOGO),
    layout="wide",
    initial_sidebar_state="expanded",
)

CURTO = {"vencido": "VENCIDO", "vence": "Vence em breve", "repor": "Repor estoque", "ok": "OK"}
OPCOES = [
    ("Todos", None, ":material/apps:"),
    ("Vencidos", "vencido", ":material/error:"),
    ("Vencem em breve", "vence", ":material/schedule:"),
    ("Repor estoque", "repor", ":material/shopping_cart:"),
    ("OK", "ok", ":material/check_circle:"),
]


@st.cache_data
def logo_base64():
    return base64.b64encode(LOGO.read_bytes()).decode()


def aplicar_estilo():
    css = (PASTA / "assets" / "estilo.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    # o calendário do Streamlit só vem em inglês: traduz meses e dias da semana
    st.html(f"<script>{(PASTA / 'assets' / 'calendario_pt.js').read_text(encoding='utf-8')}</script>", unsafe_allow_javascript=True)


def pedir_senha():
    senha = st.secrets.get("APP_PASSWORD")
    if not senha or st.session_state.get("autenticado"):
        return
    st.markdown("<style>" + (PASTA / "assets" / "login.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        with st.form("login"):
            st.markdown(
                "<div class='login-topo'>"
                f"<img src='data:image/png;base64,{logo_base64()}'>"
                "<div class='login-titulo'>CONTROLE DE ESTOQUE</div>"
                "<div class='login-sub'>Validade e estoque mínimo dos medicamentos</div>"
                "<div class='login-local'>Farmácia Descontão do Trabalhador · Centro, Araçoiaba-PE</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            digitada = st.text_input("Senha", type="password", placeholder="Digite a senha de acesso")
            entrou = st.form_submit_button("Entrar", type="primary", icon=":material/login:", width="stretch")
            if entrou:
                if digitada == senha:
                    st.session_state["autenticado"] = True
                    st.rerun()
                st.error("Senha incorreta. Tente novamente.", icon=":material/lock:")
        st.markdown("<div class='login-rodape'>Acesso restrito aos funcionários da farmácia</div>", unsafe_allow_html=True)
    st.stop()


@st.cache_resource
def conectar():
    ws = e.abrir_planilha(st.secrets["gcp_service_account"], st.secrets["SHEET_ID"])
    return e.Estoque(ws)


@st.cache_resource(ttl=30, show_spinner="Carregando estoque...")
def carregar():
    return conectar().listar(), datetime.now(FUSO)


def gravou(mensagem):
    carregar.clear()
    st.session_state["aviso"] = mensagem
    st.rerun()


def cabecalho(atualizado):
    st.markdown(
        "<div class='topo'>"
        "<div class='topo-marca'>"
        f"<div class='topo-logo'><img src='data:image/png;base64,{logo_base64()}'></div>"
        "<div><h1>Controle de Estoque</h1>"
        "<p>Farmácia Descontão do Trabalhador · Centro, Araçoiaba-PE</p></div>"
        "</div>"
        f"<div class='topo-data'><span>Atualizado em</span><b>{atualizado:%d/%m/%Y %H:%M}</b></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def barra_lateral(produtos):
    with st.sidebar:
        st.markdown(
            f"<div class='marca-lateral'><div><img src='data:image/png;base64,{logo_base64()}'></div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='rotulo-lateral'>Filtrar por situação</div>", unsafe_allow_html=True)
        atual = st.session_state.get("filtro")
        for rotulo, status, icone in OPCOES:
            n = len(produtos) if status is None else sum(p.status == status for p in produtos)
            if st.button(
                f"{rotulo} ({n})",
                key=f"filtro_{status or 'todos'}",
                icon=icone,
                type="primary" if atual == status else "secondary",
                width="stretch",
            ):
                st.session_state["filtro"] = status
                st.rerun()
        st.divider()
        if st.button("Atualizar dados", icon=":material/refresh:", use_container_width=True):
            carregar.clear()
            st.rerun()
        if produtos:
            tabela = pd.DataFrame(
                {
                    "Produto": [p.produto for p in produtos],
                    "Validade": [p.validade.strftime("%d/%m/%Y") for p in produtos],
                    "Quantidade": [p.quantidade for p in produtos],
                    "Estoque mínimo": [p.minimo for p in produtos],
                    "Situação": [CURTO[p.status] for p in produtos],
                }
            )
            st.download_button(
                "Baixar lista (CSV)",
                tabela.to_csv(index=False, sep=";").encode("utf-8-sig"),
                "estoque.csv",
                "text/csv",
                icon=":material/download:",
                use_container_width=True,
            )
        if st.secrets.get("APP_PASSWORD") and st.button("Sair", icon=":material/logout:", use_container_width=True):
            st.session_state.pop("autenticado", None)
            st.rerun()
    return st.session_state.get("filtro")


def indicadores(produtos):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Produtos cadastrados", len(produtos))
    c2.metric("Vencidos", sum(p.status == "vencido" for p in produtos))
    c3.metric(f"Vencem em até {e.DIAS_ALERTA} dias", sum(p.status == "vence" for p in produtos))
    c4.metric("Para repor", sum(p.status == "repor" for p in produtos))

    vencidos = [p.produto for p in produtos if p.status == "vencido"]
    if vencidos:
        nomes = ", ".join(vencidos[:4]) + (f" e mais {len(vencidos) - 4}" if len(vencidos) > 4 else "")
        st.error(f"**Atenção:** {len(vencidos)} produto(s) vencido(s). Retire da prateleira: {nomes}.", icon=":material/warning:")


LARGURAS = [3.2, 1.2, 1.2, 0.7, 0.8, 1.5, 1.1]


def linha_cabecalho():
    cols = st.columns(LARGURAS)
    titulos = ["Produto", "Validade", "Dias p/ vencer", "Qtd", "Mínimo", "Situação", ""]
    for col, titulo in zip(cols, titulos):
        marca = "<span class='m-cab'></span>" if titulo == "Produto" else ""
        col.markdown(f"{marca}<span class='m-cab-t'>{titulo}</span>", unsafe_allow_html=True)


def linha_produto(repo, p):
    cols = st.columns(LARGURAS)
    cols[0].markdown(f"<span class='m-{p.status}'></span><span class='m-nome'>{html.escape(p.produto)}</span>", unsafe_allow_html=True)
    cols[1].markdown(f"{p.validade:%d/%m/%Y}")
    cols[2].markdown(str(p.dias))
    cols[3].markdown(str(p.quantidade))
    cols[4].markdown(str(p.minimo))
    cols[5].markdown(f"<span class='badge badge-{p.status}'>{CURTO[p.status]}</span>", unsafe_allow_html=True)
    if cols[6].button("Editar", key=f"editar-{p.linha}", icon=":material/edit:"):
        dialogo_editar(repo, p)


@st.dialog("Editar produto")
def dialogo_editar(repo, p):
    nome = st.text_input("Produto", p.produto)
    c1, c2, c3 = st.columns([1.4, 1, 1])
    validade = c1.date_input("Validade", p.validade, format="DD/MM/YYYY")
    qtd = c2.number_input("Quantidade", min_value=0, step=1, value=p.quantidade)
    minimo = c3.number_input("Estoque mínimo", min_value=0, step=1, value=p.minimo)
    if st.button("Salvar alterações", type="primary", width="stretch"):
        try:
            repo.editar(p.linha, nome, validade, qtd, minimo, esperado=p.produto)
        except ValueError as erro:
            st.error(str(erro))
        else:
            gravou(f"{nome.strip()} atualizado.")
    st.divider()
    confirma = st.checkbox("Confirmo que quero excluir este produto")
    if st.button("Excluir produto", disabled=not confirma, icon=":material/delete:", width="stretch"):
        try:
            repo.excluir(p.linha, esperado=p.produto)
        except ValueError as erro:
            st.error(str(erro))
        else:
            gravou(f"{p.produto} excluído.")


def formulario_cadastro(repo):
    st.markdown("<div class='secao'>Cadastrar produto</div>", unsafe_allow_html=True)
    with st.form("novo", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns([3.2, 1.6, 1, 1, 1.3])
        nome = c1.text_input("Produto", placeholder="Ex.: Dipirona 500 mg comprimido")
        validade = c2.date_input("Validade", format="DD/MM/YYYY")
        qtd = c3.number_input("Quantidade", min_value=0, step=1, value=None, placeholder="0")
        minimo = c4.number_input("Estoque mínimo", min_value=0, step=1, value=None, placeholder="0")
        c5.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        enviar = c5.form_submit_button("Cadastrar", type="primary", width="stretch")
        if enviar:
            try:
                if qtd is None:
                    raise ValueError("Informe a quantidade.")
                repo.adicionar(nome, validade, qtd, minimo or 0)
            except ValueError as erro:
                st.error(str(erro))
            else:
                gravou(f"{nome.strip()} cadastrado.")


def lista_estoque(repo, produtos, filtro):
    st.markdown("<div class='secao'>Estoque</div>", unsafe_allow_html=True)
    busca = st.text_input("Buscar produto", placeholder="Digite parte do nome...", icon=":material/search:")
    visiveis = sorted(
        (p for p in produtos if busca.lower() in p.produto.lower() and (filtro is None or p.status == filtro)),
        key=lambda p: (e.ORDEM[p.status], p.validade),
    )
    if not visiveis:
        st.info("Nenhum produto encontrado." if produtos else "Nenhum produto cadastrado ainda. Use o formulário acima.")
        return

    with st.container(key="tabela"):
        linha_cabecalho()
        for p in visiveis:
            linha_produto(repo, p)

    st.markdown(
        f"<div class='legenda'>{len(visiveis)} de {len(produtos)} produtos. "
        f"Vence em breve = até {e.DIAS_ALERTA} dias.</div>",
        unsafe_allow_html=True,
    )


def main():
    aplicar_estilo()
    pedir_senha()
    if st.secrets.get("MODO_DEMO"):
        st.error("MODO DEMONSTRAÇÃO: dados fictícios, não use como evidência real.")
    if aviso := st.session_state.pop("aviso", None):
        st.toast(aviso, icon=":material/check_circle:")

    try:
        repo = conectar()
        produtos, atualizado = carregar()
    except Exception as erro:
        st.error(f"Não foi possível acessar a planilha: {erro}")
        st.stop()

    filtro = barra_lateral(produtos)
    cabecalho(atualizado)
    indicadores(produtos)
    formulario_cadastro(repo)
    lista_estoque(repo, produtos, filtro)

    st.markdown(
        "<div class='rodape'>Farmácia Descontão do Trabalhador · Projeto de extensão "
        "de Gestão de Projetos · Engenharia de Software</div>",
        unsafe_allow_html=True,
    )


main()
