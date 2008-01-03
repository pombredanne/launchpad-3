SET client_min_messages=ERROR;

ALTER TABLE CodeImportResult
    RENAME COLUMN date_started TO date_job_started;

-- XXX MichaelHudson 2008-01-03: Get a real patch number.
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 97, 0);
