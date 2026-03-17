-- Script para adicionar os campos icone e cor na tabela categoria
-- Execute este script no banco de dados PostgreSQL

-- Adicionar coluna icone
ALTER TABLE categoria ADD COLUMN IF NOT EXISTS icone VARCHAR(100) DEFAULT 'bi-tag';

-- Adicionar coluna cor
ALTER TABLE categoria ADD COLUMN IF NOT EXISTS cor VARCHAR(7) DEFAULT '#6366f1';

-- Atualizar registros existentes com valores padrao
UPDATE categoria SET icone = 'bi-tag' WHERE icone IS NULL;
UPDATE categoria SET cor = '#6366f1' WHERE cor IS NULL;
