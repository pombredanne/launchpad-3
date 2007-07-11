SET client_min_messages=ERROR;

-- Add a column.  We'll add a "not null" constraint here later, but starting
-- out with nulls lets us avoid some painfully long operations.
ALTER TABLE POMsgSet ADD COLUMN language integer REFERENCES Language(id);

-- Before we do anything more to the schema, let the database figure out that
-- the new column is all nulls.  This seems to speed up index creation.
ANALYZE POMsgSet(language);

-- We'll probably want to partition POMsgSet on this column in the future
CREATE INDEX pomsgset__language__idx ON POMsgSet(language);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 28, 0);

