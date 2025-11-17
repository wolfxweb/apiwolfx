def run(db):
    """
    Adiciona colunas de mensagem de boas-vindas configuráveis no agente:
    - welcome_message TEXT
    - welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE
    - welcome_use_model BOOLEAN NOT NULL DEFAULT FALSE
    """
    try:
        from sqlalchemy import text as sql_text
        sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'openai_assistants' AND column_name = 'welcome_message'
            ) THEN
                ALTER TABLE openai_assistants ADD COLUMN welcome_message TEXT;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'openai_assistants' AND column_name = 'welcome_enabled'
            ) THEN
                ALTER TABLE openai_assistants ADD COLUMN welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'openai_assistants' AND column_name = 'welcome_use_model'
            ) THEN
                ALTER TABLE openai_assistants ADD COLUMN welcome_use_model BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
        """
        with db.begin():
            db.execute(sql_text(sql))
        print("✅ [MIGRATION] Colunas de boas-vindas adicionadas/verificadas em openai_assistants")
    except Exception as e:
        print(f"❌ [MIGRATION] Erro ao adicionar colunas de boas-vindas: {e}")

