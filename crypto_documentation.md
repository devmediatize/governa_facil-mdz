# Módulo de Criptografia de Senhas

Módulo simples para criptografar e descriptografar senhas utilizando uma chave personalizada.

---

## Instalação

```bash
pip install cryptography python-dotenv
```

---

## Arquivo `crypto.py`

Crie o arquivo `crypto.py` no seu projeto com o seguinte conteúdo:

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def _derive_key(key: str) -> bytes:
    """Deriva a chave personalizada para o formato Fernet."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"salt_fixo_projeto",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(key.encode()))


def encrypt(password: str, key: str) -> str:
    """Criptografa a senha usando a chave fornecida."""
    fernet = Fernet(_derive_key(key))
    return fernet.encrypt(password.encode()).decode()


def decrypt(encrypted: str, key: str) -> str:
    """Descriptografa a senha usando a chave fornecida."""
    fernet = Fernet(_derive_key(key))
    return fernet.decrypt(encrypted.encode()).decode()
```

---

## Configuração

### 1. Criar arquivo `.env`

Na raiz do seu projeto, crie um arquivo `.env`:

```
ENCRYPTION_KEY=SuaChaveSecretaAqui
```

### 2. Adicionar `.env` ao `.gitignore`

```
.env
```

---

## Como Usar

### Exemplo Básico

```python
from crypto import encrypt, decrypt

KEY = "MinhaChaveSecreta"

# Criptografar
senha_criptografada = encrypt("minha_senha_123", KEY)
print(senha_criptografada)
# Resultado: gAAAAABn...

# Descriptografar
senha_original = decrypt(senha_criptografada, KEY)
print(senha_original)
# Resultado: minha_senha_123
```

### Exemplo com `.env`

```python
import os
from dotenv import load_dotenv
from crypto import encrypt, decrypt

# Carrega variáveis do .env
load_dotenv()
KEY = os.getenv("ENCRYPTION_KEY")

# Criptografar senha IMAP/SMTP
senha_imap_criptografada = encrypt("senha_do_email", KEY)

# Descriptografar quando precisar usar
senha_imap = decrypt(senha_imap_criptografada, KEY)
```

### Exemplo com Banco de Dados

```python
import os
from dotenv import load_dotenv
from crypto import encrypt, decrypt

load_dotenv()
KEY = os.getenv("ENCRYPTION_KEY")

# --- SALVANDO NO BANCO ---
senha_original = "senha_email_123"
senha_para_banco = encrypt(senha_original, KEY)

cursor.execute(
    "INSERT INTO contas_email (email, senha) VALUES (?, ?)",
    ("usuario@email.com", senha_para_banco)
)

# --- RECUPERANDO DO BANCO ---
cursor.execute("SELECT senha FROM contas_email WHERE email = ?", ("usuario@email.com",))
row = cursor.fetchone()

senha_descriptografada = decrypt(row[0], KEY)
print(senha_descriptografada)  # senha_email_123
```

---

## Estrutura do Projeto

```
seu_projeto/
├── .env                 # Contém ENCRYPTION_KEY (NÃO commitar!)
├── .gitignore           # Deve incluir .env
├── crypto.py            # Módulo de criptografia
└── main.py              # Seu código principal
```

---

## Observações Importantes

| Item | Descrição |
|------|-----------|
| **Chave** | Use uma chave forte e única para seu projeto |
| **Segurança** | Nunca commite o arquivo `.env` no repositório |
| **Backup** | Guarde a chave em local seguro. Se perder, não poderá recuperar as senhas |
| **Ambiente** | Use chaves diferentes para desenvolvimento e produção |

---

## Erros Comuns

### `InvalidToken`

Ocorre quando a chave usada para descriptografar é diferente da usada para criptografar.

```python
from cryptography.fernet import InvalidToken

try:
    senha = decrypt(senha_criptografada, KEY)
except InvalidToken:
    print("Chave inválida ou dados corrompidos")
```

---

## Fonte

Documentação criada a partir da conversa com Claude.

**Autor:** Gleidson  
**Link:** https://claude.ai/chat/383e1645-7711-4086-9ae9-a75306e4972c
