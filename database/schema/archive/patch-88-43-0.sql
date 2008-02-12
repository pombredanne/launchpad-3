SET client_min_messages=ERROR;

ALTER TABLE CodeImportResult
    RENAME COLUMN date_started TO date_job_started;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 43, 0);
