SET client_min_messages=ERROR;

-- Add a new column as per bug #180236 request.
ALTER TABLE Builder ADD COLUMN visible boolean;
ALTER TABLE Builder ALTER COLUMN visible SET DEFAULT true;

-- Make all builders 'visible'.
UPDATE Builder set visible=true;


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
