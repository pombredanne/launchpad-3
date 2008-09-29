SET client_min_messages=ERROR;

ALTER TABLE PersonLocation 
    ADD COLUMN visible boolean DEFAULT TRUE,
    ADD COLUMN locked boolean DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 70, 0);
