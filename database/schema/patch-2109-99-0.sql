SET client_min_messages=ERROR;
ALTER TABLE Product ADD COLUMN remote_product text; 
INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
