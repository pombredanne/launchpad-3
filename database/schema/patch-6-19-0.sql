INSERT INTO BugTask (
    bug,
    product,
    distribution,
    distrorelease,
    sourcepackagename,
    binarypackagename,
    status, priority, severity, assignee,
    dateassigned, datecreated, owner) 
    SELECT
        bug AS bug,
        product AS product,
        NULL AS distribution,
        NULL AS distrorelease,
        NULL AS sourcepackagename,
        NULL AS binarypackagename,
        bugstatus, priority, severity, assignee,
        dateassigned, datecreated, owner
    FROM ProductBugAssignment;

INSERT INTO BugTask (
    bug,
    product,
    distribution,
    distrorelease,
    sourcepackagename,
    binarypackagename,
    status, priority, severity, assignee,
    dateassigned, datecreated, owner) 
    SELECT
        bug AS bug,
        NULL AS product,
        (SELECT id FROM distribution WHERE name='ubuntu') AS distribution,
        NULL AS distrorelease,
        (SELECT spn.id
            FROM SourcePackageName AS spn, SourcePackage AS sp
            WHERE spn.id=sp.sourcepackagename and sp.id = sourcepackage)
            AS sourcepackagename,
        binarypackagename AS binarypackagename,
        bugstatus, priority, severity, assignee,
        dateassigned, datecreated, owner
    FROM SourcePackageBugAssignment;

DELETE FROM SourcePackageBugAssignment;
DELETE FROM ProductBugAssignment;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=19, patch=0;
