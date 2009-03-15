SET client_min_messages=ERROR;

ALTER TABLE PreviewDiff
  ALTER COLUMN dependent_revision_id DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 22, 0);
