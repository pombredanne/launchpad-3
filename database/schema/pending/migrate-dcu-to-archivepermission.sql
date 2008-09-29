/* Upload permssions for Ubuntu. */
INSERT INTO ArchivePermission (
    date_created, person, permission, archive, component, sourcepackagename)
    SELECT dcu.date_created, dcu.uploader, 1, 1, dcu.component, NULL
    FROM DistroComponentUploader as dcu
    WHERE component IN (1,2,3,4);

/* Upload permssions for the partner archive.*/
INSERT INTO ArchivePermission (
    date_created, person, permission, archive, component, sourcepackagename)
    SELECT dcu.date_created, dcu.uploader, 1, 534, dcu.component, NULL
    FROM DistroComponentUploader as dcu
    WHERE component=7;

/* Queue admin permissions for "archive-admin" */
INSERT INTO ArchivePermission (
    person, permission, archive, component, sourcepackagename)
    SELECT
        (SELECT upload_admin FROM distribution WHERE name='ubuntu') AS person,
        2 AS permission,
        1 AS archive,
        Component.id AS component,
        NULL AS sourcepackagename
    FROM Component
    WHERE name IN ('main', 'restricted', 'universe', 'multiverse');

