SET client_min_messages=ERROR;

-- Private bug searches want to use this index, and other queries
-- may well benefit too.
CREATE INDEX teamparticipation_person_idx ON TeamParticipation(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 30, 1);
