CREATE TABLE RevisionProperty (
  id serial PRIMARY KEY,
  revision integer NOT NULL CONSTRAINT revisionproperty__revision__fk REFERENCES Revision(id),
  name text NOT NULL,
  value text NOT NULL);

ALTER TABLE ONLY RevisionProperty
  ADD CONSTRAINT revisionproperty__revision__name__key UNIQUE (revision, name);


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 12, 0);
