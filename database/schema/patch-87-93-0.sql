SET client_min_messages=ERROR;

ALTER TABLE Branch
  ADD COLUMN date_last_modified TIMESTAMP WITHOUT TIME ZONE;

/*
The date_last_modified for a branch is the maximum of the
date_created of the tip revision or the date the branch was created.
*/

UPDATE Branch
SET date_last_modified = date_created;

UPDATE Branch
SET date_last_modified = Revision.date_created
FROM Revision
WHERE Branch.last_scanned_id = Revision.revision_id
AND Revision.date_created > Branch.date_last_modified;

ALTER TABLE Branch
  ALTER COLUMN date_last_modified SET NOT NULL,
  ALTER COLUMN date_last_modified SET DEFAULT timezone('UTC'::text, now());

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 93, 0);

