# Sistema de Gestão Interativa

## Requisitos
- Python 3.8+
- PostgreSQL 12+

## Instalação

1. Clone o repositório:
```bash
git clone [url-do-repositorio]
cd sistema_incidencias
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o arquivo .env:
```
DATABASE_URL=postgresql://user:password@localhost/db_name
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Crie o banco de dados PostgreSQL e execute o script SQL fornecido

6. Inicie o servidor:
```bash
uvicorn app.main:app --reload
```

O sistema estará disponível em `http://localhost:8000`

## Funcionalidades
- Autenticação JWT
- Gerenciamento de usuários
- Gerenciamento de incidências
- Upload de fotos
- Dashboard com estatísticas
- Gerenciamento de categorias e status

## Estrutura do Projeto
- `app/`: Código principal da aplicação
  - `main.py`: Arquivo principal com as rotas
  - `models.py`: Modelos SQLAlchemy
  - `schemas.py`: Schemas Pydantic
  - `database.py`: Configuração do banco de dados
  - `auth.py`: Sistema de autenticação
- `templates/`: Templates HTML
- `static/`: Arquivos estáticos (CSS, JS, imagens)

## API Documentation
A documentação da API está disponível em:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
