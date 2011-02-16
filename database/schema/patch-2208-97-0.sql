SET client_min_messages=ERROR;

CREATE TABLE FeatureFlagChange (
    id serial NOT NULL,
    date_changed timestamp without time zone NOT NULL
        DEFAULT timezone('UTC'::text, now()),
    diff text NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 97, 0);
