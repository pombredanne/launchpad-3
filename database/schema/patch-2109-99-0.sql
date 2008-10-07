SET client_min_messages=ERROR;

-- Adding a 'status' column for better handling failed request.
ALTER TABLE PackageDiff ADD COLUMN status INTEGER;

-- Set the default value so the NOT NULL constraint can be added.
-- A proper data migration will be done when the new code gets released.
UPDATE PackageDiff SET status = 0;

-- Column contraints.
ALTER TABLE PackageDiff ALTER COLUMN status SET NOT NULL;
ALTER TABLE PackageDiff ALTER COLUMN status SET DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
