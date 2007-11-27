SET client_min_messages=ERROR;

-- Rename mirror_request_time to next_mirror_time
ALTER TABLE branch RENAME COLUMN mirror_request_time TO next_mirror_time;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
