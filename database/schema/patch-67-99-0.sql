SET client_min_messages=ERROR;

ALTER TABLE branch ADD COLUMN revision_count integer;
ALTER TABLE branch ADD COLUMN tip_revision integer;

ALTER TABLE ONLY branch
  ADD CONSTRAINT branch__tip_rev_fk
    FOREIGN KEY (tip_revision) REFERENCES revision(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);