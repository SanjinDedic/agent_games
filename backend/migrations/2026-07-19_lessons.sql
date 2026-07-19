-- Lessons: standalone markdown documents (with runnable ```python-run
-- fences) opened from lesson://<slug> links inside exercise problem markdown
-- and tutorial descriptions. Global content library, not league-gated.
--
-- Matches what create_all emits for the Lesson model: unique+index on slug
-- becomes a single UNIQUE INDEX named ix_lesson_slug (not a UNIQUE
-- constraint), and created_at is nullable — the model supplies the default.
--
-- Idempotent: once the table exists this whole script is a no-op.

DO $$
BEGIN
    IF to_regclass('public.lesson') IS NULL THEN
        CREATE TABLE lesson (
            id SERIAL PRIMARY KEY,
            slug VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE
        );
        CREATE UNIQUE INDEX ix_lesson_slug ON lesson (slug);
    END IF;
END $$;
