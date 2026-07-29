-- Exercise hint reveals: one row the first time a student opens a given hint
-- of an exercise. Exercise hints are static authored nudges rendered entirely
-- in the browser, so until now nothing recorded that a student needed one.
-- Concept mastery counts a revealed hint as extra effort alongside the number
-- of attempts, which is why the reveal has to reach the server.
--
-- The unique constraint is the point, not an afterthought: the client fires
-- this on every reveal, including after a reload, and the insert is expected
-- to collide and no-op rather than inflate the count.
--
-- Matches what create_all emits for the ExerciseHintReveal model: team_id is
-- nullable (demo-user cleanup nulls child FKs, same as
-- exercisesubmissionmetadata), revealed_at is nullable because the model
-- supplies the default, and the UniqueConstraint becomes a table constraint
-- rather than an index.
--
-- Idempotent: once the table exists this whole script is a no-op. No backfill
-- is possible — reveals before this migration were never recorded anywhere.

DO $$
BEGIN
    IF to_regclass('public.exercisehintreveal') IS NULL THEN
        CREATE TABLE exercisehintreveal (
            id SERIAL PRIMARY KEY,
            team_id INTEGER REFERENCES team (id),
            exercise_id INTEGER NOT NULL REFERENCES exercise (id),
            hint_index INTEGER NOT NULL,
            revealed_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT exercisehintreveal_team_id_exercise_id_hint_index_key
                UNIQUE (team_id, exercise_id, hint_index)
        );
        CREATE INDEX ix_exercisehintreveal_team_id
            ON exercisehintreveal (team_id);
        CREATE INDEX ix_exercisehintreveal_exercise_id
            ON exercisehintreveal (exercise_id);
    END IF;
END $$;
