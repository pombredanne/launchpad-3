SET client_min_messages=ERROR;

ALTER TABLE Person 
ADD COLUMN private_membership boolean DEFAULT false NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
