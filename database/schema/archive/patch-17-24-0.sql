
set client_min_messages=ERROR;

ALTER TABLE DistroRelease ADD COLUMN datelastlangpack TIMESTAMP WITHOUT
TIME ZONE;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 24, 0);

