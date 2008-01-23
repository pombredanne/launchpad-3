SET client_min_messages=ERROR;

ALTER TABLE RevisionAuthor
  ADD COLUMN email text;

ALTER TABLE RevisionAuthor
  ADD COLUMN person int REFERENCES (Person);


-- Need indexes for people merge
CREATE INDEX revisionauthor__person__idx
  ON RevisionAuthor(person);


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 92, 0);
