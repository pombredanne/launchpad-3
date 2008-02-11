SET client_min_messages=ERROR;

-- Add a new column as per bug #180236 request.
ALTER TABLE Builder ADD COLUMN active boolean DEFAULT TRUE NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 46, 0);
