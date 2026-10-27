# Controle de Estoque - Streamlit + Google Sheets

Banco de dados: uma planilha do Google Sheets. A tela (Streamlit) lê e grava nela.

## 1. Configurar o Google (uma vez só, uns 20 minutos)
1. Entre em console.cloud.google.com com uma conta Google pessoal e crie um **projeto** (ex.: "estoque-farmacia").
2. Em **APIs e serviços > Biblioteca**, ative a **Google Sheets API** e a **Google Drive API**.
3. Em **IAM e administrador > Contas de serviço**, crie uma conta de serviço (nome livre, sem funções).
4. Abra a conta criada > aba **Chaves** > **Adicionar chave > Criar nova chave > JSON**. Um arquivo `.json` é baixado. **Não publique esse arquivo.**
5. Em sheets.google.com crie uma planilha em branco (a linha 1 é criada pelo sistema).
6. Clique em **Compartilhar** e adicione o e-mail da conta de serviço (campo `client_email` do JSON) como **Editor**.
7. Copie o ID da planilha: é o trecho da URL entre `/d/` e `/edit`.

## 2. Configurar os segredos
Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha:
- `APP_PASSWORD`: senha para entrar no sistema.
- `SHEET_ID`: o ID do passo 7.
- `[gcp_service_account]`: copie os campos do JSON baixado (`project_id`, `private_key_id`, `private_key`, `client_email`, `client_id`).

## 3. Rodar no computador
```
pip install -r requirements.txt
streamlit run app.py
```

## 4. Publicar com link (Streamlit Community Cloud)
1. Crie um repositório no GitHub com esta pasta (o `.gitignore` já impede o envio dos segredos).
2. Em share.streamlit.io, crie o app apontando para `app.py`.
3. Em **Settings > Secrets**, cole o conteúdo do seu `secrets.toml`.

## Regras dos alertas
- VENCIDO: validade anterior a hoje.
- Vence em até 90 dias.
- Repor estoque: quantidade menor ou igual ao estoque mínimo.

## Atenção
- Planilha de teste e planilha real devem ser **separadas**. Para a de teste, use `MODO_DEMO = true` nos segredos (mostra uma faixa de aviso).
- Não coloque o arquivo JSON nem o `secrets.toml` no GitHub.
