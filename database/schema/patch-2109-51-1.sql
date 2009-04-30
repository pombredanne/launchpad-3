SET client_min_messages=ERROR;

create index translationmessage__pofile__idx on translationmessage(pofile);
create index pofiletranslator__pofile__idx on pofiletranslator(pofile);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 51, 1);
