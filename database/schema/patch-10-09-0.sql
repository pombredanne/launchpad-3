SET client_min_messages=ERROR;

ALTER TABLE BugTask
DROP CONSTRAINT bugtask_assignment_checks;

ALTER TABLE BugTask
ADD CONSTRAINT bugtask_assignment_checks
CHECK (
    CASE
        WHEN (product IS NOT NULL) THEN distribution IS NULL AND distrorelease IS NULL
        WHEN (distribution IS NOT NULL) THEN product IS NULL AND distrorelease IS NULL
        WHEN (distrorelease IS NOT NULL) THEN product IS NULL AND distribution IS NULL
    END
);

INSERT INTO LaunchpadDatabaseRevision VALUES (10,9,0);

