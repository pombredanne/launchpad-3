SET client_min_messages=ERROR;

-- Rename mirror_request_time to next_mirror_time
ALTER TABLE branch RENAME COLUMN mirror_request_time TO next_mirror_time;

CREATE INDEX branch__next_mirror_time__idx ON Branch(next_mirror_time)
WHERE next_mirror_time IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 32, 0);
