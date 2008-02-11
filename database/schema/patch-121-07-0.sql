SET client_min_messages=ERROR;

ALTER TABLE RevisionAuthor
  ADD COLUMN email text;

ALTER TABLE RevisionAuthor
  ADD COLUMN person int REFERENCES Person;

-- Revision.owner is a useless field and is always set to be
-- the launchpad administrator team.
ALTER TABLE Revision
  DROP COLUMN owner;
-- stub: will this automatically drop the index associated
--   with this column?

-- Need indexes for people merge
CREATE INDEX revisionauthor__email__idx
  ON RevisionAuthor(email);
CREATE INDEX revisionauthor__person__idx
  ON RevisionAuthor(person);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 7, 0);
