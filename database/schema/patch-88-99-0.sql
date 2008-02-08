SET client_min_messages=ERROR;

ALTER TABLE MessageApproval
    ADD COLUMN status_reason_text text;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
