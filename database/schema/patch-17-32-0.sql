SET client_min_messages=ERROR;

CREATE INDEX wikiname_person_idx ON WikiName(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 32, 0);

