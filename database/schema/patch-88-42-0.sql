SET client_min_messages=ERROR;

ALTER TABLE Project ADD COLUMN reviewer_whiteboard text;
ALTER TABLE Product ADD COLUMN reviewer_whiteboard text;
ALTER TABLE Distribution ADD COLUMN reviewer_whiteboard text;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 42, 0);
