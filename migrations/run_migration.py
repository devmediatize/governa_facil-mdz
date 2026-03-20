"""
Script para executar migracao de adicao dos campos de notificacao
Execute: python migrations/run_migration.py
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from dotenv import load_dotenv
from app.database import engine

load_dotenv()

def run_migration():
    """Executa a migracao para adicionar campos de notificacao"""

    migration_sql = """
    -- Adicionar campo receber_alertas_email na tabela usuario
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuario' AND column_name='receber_alertas_email') THEN
            ALTER TABLE usuario ADD COLUMN receber_alertas_email INTEGER DEFAULT 1;
            RAISE NOTICE 'Coluna receber_alertas_email adicionada';
        ELSE
            RAISE NOTICE 'Coluna receber_alertas_email ja existe';
        END IF;
    END $$;

    -- Adicionar campo receber_alertas_sistema na tabela usuario
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuario' AND column_name='receber_alertas_sistema') THEN
            ALTER TABLE usuario ADD COLUMN receber_alertas_sistema INTEGER DEFAULT 1;
            RAISE NOTICE 'Coluna receber_alertas_sistema adicionada';
        ELSE
            RAISE NOTICE 'Coluna receber_alertas_sistema ja existe';
        END IF;
    END $$;

    -- Atualizar registros existentes para terem os valores padrao
    UPDATE usuario SET receber_alertas_email = 1 WHERE receber_alertas_email IS NULL;
    UPDATE usuario SET receber_alertas_sistema = 1 WHERE receber_alertas_sistema IS NULL;
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
            print("Migracao executada com sucesso!")
            print("Campos adicionados:")
            print("  - receber_alertas_email (INTEGER, default 1)")
            print("  - receber_alertas_sistema (INTEGER, default 1)")
    except Exception as e:
        print(f"Erro ao executar migracao: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Executando migracao: Adicionar campos de notificacao...")
    run_migration()
