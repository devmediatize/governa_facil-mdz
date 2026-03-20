-- Migracao: Adicionar campo foto na tabela incidencia_interacao
-- Data: 2026-03-20
-- Sistema: Governa Facil
-- Banco: PostgreSQL

-- Adicionar campo foto na tabela incidencia_interacao
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='incidencia_interacao' AND column_name='foto') THEN
        ALTER TABLE incidencia_interacao ADD COLUMN foto VARCHAR(500) NULL;
    END IF;
END $$;

-- Comentario: O campo foto armazena o caminho da imagem associada a interacao
-- As fotos sao armazenadas no MinIO/S3 ou localmente em /fotos/interacoes/
