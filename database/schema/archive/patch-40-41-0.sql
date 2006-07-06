SET client_min_messages=ERROR;

ALTER TABLE Person DROP CONSTRAINT valid_team_fields;
ALTER TABLE Person DROP COLUMN givenname;
ALTER TABLE Person DROP COLUMN familyname;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 41, 0);

