SET client_min_messages=ERROR;

create index translationmessage__pofile__idx on translationmessage(pofile);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 51, 1);
