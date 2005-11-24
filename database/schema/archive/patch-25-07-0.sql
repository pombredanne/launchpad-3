SET client_min_messages=ERROR;

-- Delete duplicate product bugtasks
DELETE FROM BugTask WHERE id IN (
    SELECT BugTask.id FROM BugTask JOIN (
        SELECT min(id) AS min_id, bug, product FROM BugTask
        WHERE product IS NOT NULL
        GROUP BY bug,product HAVING count(id) > 1
        ) AS Duds ON BugTask.product = Duds.product AND BugTask.bug = Duds.bug
        WHERE BugTask.id <> min_id
        );

-- Stop duplicate upstream bugtasks
--ALTER TABLE BugTask ADD CONSTRAINT bugtask_product_key UNIQUE (product, bug);
CREATE UNIQUE INDEX bugtask_product_key ON BugTask (product, bug)
    WHERE product IS NOT NULL;

-- Drop pointless index
DROP INDEX bugtask_product_idx;


-- DELETE duplicate distro bugtasks
DELETE FROM BugTask WHERE id IN (
    SELECT BugTask.id FROM BugTask JOIN (
        SELECT min(id) as min_id,
            bug, distribution, distrorelease, sourcepackagename
        FROM BugTask
        WHERE product IS NULL
        GROUP BY bug, distribution, distrorelease, sourcepackagename
        HAVING count(id) > 1
        ) AS Duds ON
            BugTask.bug = Duds.bug
            AND COALESCE(BugTask.distribution,-1)
                = COALESCE(Duds.distribution,-1)
            AND COALESCE(BugTask.distrorelease,-1)
                = COALESCE(Duds.distrorelease,-1)
            AND COALESCE(BugTask.sourcepackagename,-1)
                = COALESCE(Duds.sourcepackagename,-1)
        WHERE BugTask.id <> min_id
        );

CREATE UNIQUE INDEX bugtask_distinct_sourcepackage_assignment ON
    BugTask(bug, (COALESCE(sourcepackagename, -1)),
        (COALESCE(distrorelease, -1)), (COALESCE(distribution, -1))
        )
    WHERE product IS NULL;

ALTER TABLE BugTask DROP CONSTRAINT bugtask_assignment_checks;
ALTER TABLE BugTask ADD CONSTRAINT bugtask_assignment_checks CHECK (
    CASE
        WHEN product IS NOT NULL THEN
            distribution IS NULL AND distrorelease IS NULL
            AND sourcepackagename IS NULL
        WHEN distribution IS NOT NULL THEN distrorelease IS NULL
        ELSE NULL
    END);


INSERT INTO LaunchpadDatabaseRevision VALUES (25,7,0);

