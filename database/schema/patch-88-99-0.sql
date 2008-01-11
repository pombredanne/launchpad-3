SET client_min_messages=ERROR;

-- Add a new column as per bug #180236 request.
ALTER TABLE Builder ADD COLUMN active boolean;
ALTER TABLE Builder ALTER COLUMN active SET DEFAULT true;

-- Make all builders 'active'.
UPDATE Builder set active=true;


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
