SET client_min_messages=ERROR;

ALTER TABLE branch ADD COLUMN revision_count integer NOT NULL DEFAULT(0);

UPDATE branch
SET revision_count = (SELECT count(*) FROM revisionnumber
                      WHERE revisionnumber.branch = branch.id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
