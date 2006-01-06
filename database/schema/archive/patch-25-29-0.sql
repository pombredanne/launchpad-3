set client_min_messages=ERROR;

ALTER TABLE Vote ALTER COLUMN preference DROP NOT NULL;
ALTER TABLE Vote DROP CONSTRAINT vote_token_key;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,29,0);
