-- Concepts: a flat, controlled vocabulary of teachable ideas, tagged onto
-- exercises and lessons. This is the foundation for concept-level analysis —
-- which concepts a student is struggling with, searching exercises by
-- concept, and listing the concepts a tutorial covers (derived as the union
-- over its exercises, so tutorials get no table of their own).
--
-- Link tables rather than a JSON column on exercise/lesson: the point is to
-- join and aggregate against submission history, and they leave the admin
-- exercise editor's write path untouched.
--
-- Matches what create_all emits for the Concept/ExerciseConcept/LessonConcept
-- models: unique+index on slug becomes a single UNIQUE INDEX named
-- ix_concept_slug (not a UNIQUE constraint), category is an unindexed
-- nullable VARCHAR, and created_at is nullable — the model supplies the
-- default. The link tables mirror leaguetutorial.
--
-- Idempotent: once each table exists this whole script is a no-op. No
-- backfill — every table starts empty.

DO $$
BEGIN
    IF to_regclass('public.concept') IS NULL THEN
        CREATE TABLE concept (
            id SERIAL PRIMARY KEY,
            slug VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE
        );
        CREATE UNIQUE INDEX ix_concept_slug ON concept (slug);
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.exerciseconcept') IS NULL THEN
        CREATE TABLE exerciseconcept (
            id SERIAL PRIMARY KEY,
            exercise_id INTEGER NOT NULL REFERENCES exercise (id),
            concept_id INTEGER NOT NULL REFERENCES concept (id),
            CONSTRAINT exerciseconcept_exercise_id_concept_id_key
                UNIQUE (exercise_id, concept_id)
        );
        CREATE INDEX ix_exerciseconcept_exercise_id
            ON exerciseconcept (exercise_id);
        CREATE INDEX ix_exerciseconcept_concept_id
            ON exerciseconcept (concept_id);
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.lessonconcept') IS NULL THEN
        CREATE TABLE lessonconcept (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lesson (id),
            concept_id INTEGER NOT NULL REFERENCES concept (id),
            CONSTRAINT lessonconcept_lesson_id_concept_id_key
                UNIQUE (lesson_id, concept_id)
        );
        CREATE INDEX ix_lessonconcept_lesson_id
            ON lessonconcept (lesson_id);
        CREATE INDEX ix_lessonconcept_concept_id
            ON lessonconcept (concept_id);
    END IF;
END $$;
