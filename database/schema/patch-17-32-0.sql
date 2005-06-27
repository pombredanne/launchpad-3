SET client_min_messages=ERROR;

CREATE INDEX wikiname_person_idx ON WikiName(person);
ALTER TABLE WikiName DROP CONSTRAINT wikiname_wiki_key;
ALTER TABLE WikiName ADD CONSTRAINT wikiname_wikiname_key UNIQUE(wikiname,wiki);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 32, 0);

