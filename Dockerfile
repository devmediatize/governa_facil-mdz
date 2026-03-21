# Use uma versão estável do Python (3.10, pois 3.13 pode ter problemas de compatibilidade)
FROM python:3.10-slim

# Defina o diretório de trabalho no contêiner
WORKDIR /app

# Instale dependências do sistema necessárias para pacotes Python e Rust
RUN apt-get update && apt-get install -y \
    curl build-essential gcc libpq-dev libssl-dev libffi-dev cargo && \
    rm -rf /var/lib/apt/lists/*

# Instale Rust e Cargo corretamente
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

# Atualizar Rust, Cargo e Python PIP
RUN rustup update stable && cargo --version && \
    pip install --upgrade pip setuptools wheel

# Exponha a porta que o aplicativo irá rodar
EXPOSE 8000

# Comando padrão: instala dependências via volume e sobe o Uvicorn
CMD ["sh", "-c", "pip install --no-cache-dir -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
