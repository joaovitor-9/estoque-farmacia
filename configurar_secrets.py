"""Cria .streamlit/secrets.toml a partir da chave JSON do Google e do ID da planilha.
Nada é impresso na tela: a chave só é lida e gravada no arquivo local."""
import getpass
import json
import sys
from pathlib import Path

ALVO = Path(__file__).parent / ".streamlit" / "secrets.toml"
CAMPOS = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri"]


def toml(valor):
    # string básica do JSON também é string básica válida em TOML
    return json.dumps(valor, ensure_ascii=False)


def gerar(caminho_json, sheet_id, senha):
    chave = json.loads(Path(caminho_json).read_text(encoding="utf-8"))
    faltando = [c for c in CAMPOS if c not in chave]
    if faltando:
        raise ValueError(f"O JSON não parece ser uma chave de conta de serviço (faltam: {faltando}).")
    linhas = [f"APP_PASSWORD = {toml(senha)}", f"SHEET_ID = {toml(sheet_id)}", "", "[gcp_service_account]"]
    linhas += [f"{c} = {toml(chave[c])}" for c in CAMPOS]
    return "\n".join(linhas) + "\n", chave["client_email"]


def main():
    if ALVO.exists():
        print("Já existe .streamlit/secrets.toml; nada foi alterado. Apague-o para refazer.")
        return 1
    caminho = input("Caminho do arquivo .json baixado do Google: ").strip().strip('"')
    sheet_id = input("ID da planilha (trecho da URL entre /d/ e /edit): ").strip()
    senha = getpass.getpass("Senha para entrar no sistema (não aparece ao digitar): ").strip()
    if not (caminho and sheet_id and senha):
        print("Preencha os três campos.")
        return 1
    try:
        texto, email = gerar(caminho, sheet_id, senha)
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"Erro: {erro}")
        return 1
    ALVO.parent.mkdir(exist_ok=True)
    ALVO.write_text(texto, encoding="utf-8")
    print("Pronto: .streamlit/secrets.toml criado (está fora do Git).")
    print(f"Confirme que a planilha está compartilhada como Editor com: {email}")
    print("Depois mova o .json para um lugar seguro ou apague-o da pasta Downloads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
