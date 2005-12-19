SET client_min_messages=ERROR;

ALTER TABLE LoginToken ADD COLUMN redirection_url text;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 12, 0);

