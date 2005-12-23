SET client_min_messages=ERROR;

CREATE TABLE FtiCache (
    id          serial PRIMARY KEY,
    tablename   text UNIQUE NOT NULL,
    columns     text NOT NULL
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 11, 0);

