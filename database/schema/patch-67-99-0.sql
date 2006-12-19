SET client_min_messages=ERROR;

ALTER TABLE branch ADD COLUMN revision_count integer;

UPDATE branch
SET revision_count = (SELECT count(*) FROM revisionnumber
                      WHERE revisionnumber.branch = branch.id);

UPDATE branch
SET revision_count = NULL
where revision_count = 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
