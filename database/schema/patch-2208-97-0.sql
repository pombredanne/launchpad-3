SET client_min_messages=ERROR;

CREATE TABLE FeatureFlagChangelogEntry (
    id serial PRIMARY KEY,
    date_changed TIMESTAMP without time zone NOT NULL
        DEFAULT timezone('UTC'::text, now()),
    diff text NOT NULL,
    "comment" text NOT NULL,
    person INTEGER NOT NULL REFERENCES person (id));


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 97, 0);
