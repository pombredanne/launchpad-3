BEGIN;

CREATE TABLE Diff (
  id serial PRIMARY KEY,
  bytes integer NOT NULL
    CONSTRAINT diff__bytes__fk REFERENCES LibraryFileAlias,
  conflicts text,
  from_revision integer
    CONSTRAINT from_revision__revision__fk REFERENCES Revision,
  to_revision integer
    CONSTRAINT to_revision__revision__fk REFERENCES Revision
);


CREATE TABLE StaticDiffReference (
  id serial PRIMARY KEY,
  branch integer NOT NULL
    CONSTRAINT staticdiffreference__branch__fk REFERENCES Branch,
  from_revision_spec text,
  to_revision_spec text,
  diff integer
    CONSTRAINT staticdiffreference__diff__fk REFERENCES Diff
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
COMMIT;
