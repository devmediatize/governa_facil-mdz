# test.py (na pasta raiz)
from fastapi import FastAPI
from app.main import processar_pergunta
from app.database import SessionLocal

app = FastAPI()  # Esta linha é crucial

# Pergunta do usuário
pergunta = "Qual são os 10 bairros que mais teve incidências de buracos?"

# Criar uma sessão de banco de dados
db = SessionLocal()

# Processar a pergunta e obter os resultados
resultados = processar_pergunta(pergunta, db)

# Exibir os resultados
for linha in resultados:
    print(linha)

# Fechar a sessão de banco de dados
db.close()