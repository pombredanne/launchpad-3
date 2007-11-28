SET client_min_messages=ERROR;

ALTER TABLE branch ADD COLUMN revision_count integer;

UPDATE branch
SET revision_count = rev_count
FROM (
    SELECT branch, count(*) AS rev_count
    FROM RevisionNumber
    GROUP BY branch
    ) AS whatever
WHERE branch = branch.id;

UPDATE branch SET revision_count=0 WHERE revision_count IS NULL;

ALTER TABLE branch ALTER COLUMN revision_count SET DEFAULT(0);
ALTER TABLE branch ALTER COLUMN revision_count SET NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 38, 0);