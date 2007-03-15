CREATE TABLE RevisionProperty (
  id serial,
  revision integer NOT NULL CONSTRAINT revisionproperty_fk REFERENCES Revision(id),
  name text NOT NULL,
  value text NOT NULL);

ALTER TABLE ONLY RevisionProperty
  ADD CONSTRAINT revisionproperty_revision_name_uniq UNIQUE (revision, name);


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
