-- Migracao: Adicionar campos de configuracao de notificacoes na tabela usuario
-- Data: 2026-03-18
-- Sistema: Governa Facil
-- Banco: PostgreSQL

-- Adicionar campo receber_alertas_email na tabela usuario
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuario' AND column_name='receber_alertas_email') THEN
        ALTER TABLE usuario ADD COLUMN receber_alertas_email INTEGER DEFAULT 1;
    END IF;
END $$;

-- Adicionar campo receber_alertas_sistema na tabela usuario
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuario' AND column_name='receber_alertas_sistema') THEN
        ALTER TABLE usuario ADD COLUMN receber_alertas_sistema INTEGER DEFAULT 1;
    END IF;
END $$;

-- Atualizar registros existentes para terem os valores padrao
UPDATE usuario SET receber_alertas_email = 1 WHERE receber_alertas_email IS NULL;
UPDATE usuario SET receber_alertas_sistema = 1 WHERE receber_alertas_sistema IS NULL;

-- Comentario: A coluna notifica_email ja existe na tabela usuario_categoria
-- e sera utilizada para controlar notificacoes por categoria especifica
