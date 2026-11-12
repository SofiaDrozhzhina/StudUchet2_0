-- МИГРАЦИЯ СТАРОЙ БАЗЫ StudUchet НА НОВУЮ СТРУКТУРУ.
-- Выполнять один раз в Query Tool базы studuchet, если база уже была создана по старому schema.sql.
-- Существующие студенты, группы и документы сохраняются.
BEGIN;

CREATE TABLE IF NOT EXISTS specialties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE study_groups ADD COLUMN IF NOT EXISTS specialty_id INTEGER;

-- Переносим существующие названия специальностей из старого текстового поля study_groups.specialty.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'study_groups' AND column_name = 'specialty'
    ) THEN
        INSERT INTO specialties(name)
        SELECT DISTINCT btrim(specialty)
        FROM study_groups
        WHERE specialty IS NOT NULL AND btrim(specialty) <> ''
        ON CONFLICT (name) DO NOTHING;

        UPDATE study_groups g
        SET specialty_id = sp.id
        FROM specialties sp
        WHERE btrim(COALESCE(g.specialty, '')) = sp.name
          AND g.specialty_id IS NULL;
    END IF;
END $$;

INSERT INTO specialties(name) VALUES ('Не указана') ON CONFLICT (name) DO NOTHING;
UPDATE study_groups SET specialty_id = (SELECT id FROM specialties WHERE name='Не указана') WHERE specialty_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'study_groups_specialty_id_fkey'
          AND conrelid = 'study_groups'::regclass
    ) THEN
        ALTER TABLE study_groups
            ADD CONSTRAINT study_groups_specialty_id_fkey
            FOREIGN KEY (specialty_id) REFERENCES specialties(id)
            ON UPDATE CASCADE ON DELETE RESTRICT;
    END IF;
END $$;

ALTER TABLE students ADD COLUMN IF NOT EXISTS student_number VARCHAR(30) NOT NULL DEFAULT '';
ALTER TABLE students ADD COLUMN IF NOT EXISTS snils VARCHAR(20) NOT NULL DEFAULT '';
ALTER TABLE students ADD COLUMN IF NOT EXISTS email VARCHAR(254) NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_students_number ON students(student_number);
CREATE INDEX IF NOT EXISTS idx_students_snils ON students(snils);
COMMIT;
