SET client_min_messages=ERROR;

CREATE INDEX revisionauthor__lower_email__idx ON RevisionAuthor(lower(email));

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 55, 2);
