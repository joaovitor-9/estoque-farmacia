"""Regras do estoque e acesso à planilha do Google Sheets (sem Streamlit na lógica)."""
from dataclasses import dataclass
from datetime import date, datetime

import gspread

DIAS_ALERTA = 90
CABECALHO = ["Produto", "Validade", "Quantidade", "Estoque mínimo"]
ROTULO = {
    "vencido": "VENCIDO",
    "vence": f"Vence em até {DIAS_ALERTA} dias",
    "repor": "Repor estoque",
    "ok": "OK",
}
ORDEM = {"vencido": 0, "vence": 1, "repor": 2, "ok": 3}

MAX_NOME = 100
MAX_QUANTIDADE = 100000
ANO_MIN, ANO_MAX = 2000, 2100


@dataclass
class Produto:
    linha: int  # número da linha na planilha
    produto: str
    validade: date
    quantidade: int
    minimo: int

    @property
    def status(self):
        return calcular_status(self.validade, self.quantidade, self.minimo)

    @property
    def dias(self):
        return (self.validade - date.today()).days


def calcular_status(validade, quantidade, minimo):
    if validade < date.today():
        return "vencido"
    if (validade - date.today()).days <= DIAS_ALERTA:
        return "vence"
    if quantidade <= minimo:
        return "repor"
    return "ok"


def para_data(valor):
    """Aceita 2027-01-31 (como o app grava) ou 31/01/2027 (se alguém digitar na planilha)."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError(f"Validade inválida: {texto!r}")


def _inteiro(valor, artigo, nome):
    if isinstance(valor, bool) or valor is None or valor == "":
        raise ValueError(f"Informe {artigo} {nome}.")
    try:
        numero = int(valor)
        inteiro = numero == float(valor)
    except (TypeError, ValueError):
        inteiro = False
    if not inteiro or numero < 0:
        raise ValueError(f"{nome.capitalize()}: use um número inteiro, 0 ou maior (sem vírgula).")
    if numero > MAX_QUANTIDADE:
        raise ValueError(f"{nome.capitalize()}: o máximo é {MAX_QUANTIDADE}. Confira o número.")
    return numero


def validar(produto, validade, quantidade, minimo):
    produto = " ".join((produto or "").split())  # tira espaços repetidos e nas pontas
    if not produto:
        raise ValueError("Informe o nome do produto.")
    if len(produto) > MAX_NOME:
        raise ValueError(f"O nome do produto pode ter no máximo {MAX_NOME} caracteres.")
    if not any(c.isalpha() for c in produto):
        raise ValueError("O nome do produto precisa ter letras (ex.: Dipirona 500 mg).")
    try:
        validade = para_data(validade)
    except ValueError:
        raise ValueError("Informe uma validade válida.")
    if not ANO_MIN <= validade.year <= ANO_MAX:
        raise ValueError(f"Validade fora do esperado (ano entre {ANO_MIN} e {ANO_MAX}).")
    return produto, validade, _inteiro(quantidade, "a", "quantidade"), _inteiro(minimo, "o", "estoque mínimo")


def abrir_planilha(credenciais, planilha_id):
    """Abre a primeira aba da planilha e cria o cabeçalho se ela estiver vazia."""
    cliente = gspread.service_account_from_dict(dict(credenciais))
    ws = cliente.open_by_key(planilha_id).sheet1
    if not ws.row_values(1):
        ws.update("A1:D1", [CABECALHO])
    return ws


class Estoque:
    def __init__(self, ws):
        self.ws = ws

    def listar(self):
        linhas = self.ws.get_all_values()[1:]
        produtos = []
        for i, l in enumerate(linhas, start=2):
            l = l + [""] * (4 - len(l))
            if not l[0].strip():
                continue
            try:
                produtos.append(Produto(i, l[0].strip(), para_data(l[1]), int(l[2] or 0), int(l[3] or 0)))
            except ValueError:
                raise ValueError(
                    f"A linha {i} da planilha ({l[0].strip()}) tem um valor inválido na validade, quantidade ou mínimo. "
                    "Corrija direto no Google Sheets."
                )
        return produtos

    def _conferir_duplicado(self, produto, validade, ignorar_linha=None):
        for p in self.listar():
            if p.linha != ignorar_linha and p.produto.casefold() == produto.casefold() and p.validade == validade:
                raise ValueError(f"{p.produto} com validade {validade:%d/%m/%Y} já está cadastrado. Edite a quantidade dele.")

    def _conferir_linha(self, linha, esperado):
        """Evita mexer no produto errado se alguém alterou a planilha desde que a lista foi carregada."""
        if esperado is None:
            return
        atual = (self.ws.row_values(linha) or [""])[0].strip()
        if atual != esperado:
            raise ValueError("A lista mudou enquanto você editava. Clique em Atualizar dados e tente de novo.")

    def adicionar(self, produto, validade, quantidade, minimo):
        p, v, q, m = validar(produto, validade, quantidade, minimo)
        self._conferir_duplicado(p, v)
        self.ws.append_row([p, v.isoformat(), q, m], value_input_option="RAW")

    def editar(self, linha, produto, validade, quantidade, minimo, esperado=None):
        p, v, q, m = validar(produto, validade, quantidade, minimo)
        self._conferir_linha(linha, esperado)
        self._conferir_duplicado(p, v, ignorar_linha=linha)
        self.ws.update(f"A{linha}:D{linha}", [[p, v.isoformat(), q, m]], value_input_option="RAW")

    def excluir(self, linha, esperado=None):
        self._conferir_linha(linha, esperado)
        self.ws.delete_rows(linha)
