INSERT INTO ArchivePermission (
    date_created, person, permission, archive, component, sourcepackagename)
    SELECT dcu.date_created, dcu.uploader, 1, 1, dcu.component, NULL
    FROM DistroComponentUploader as dcu
    WHERE component IN (1,2,3,4);

INSERT INTO ArchivePermission (
    date_created, person, permission, archive, component, sourcepackagename)
    SELECT dcu.date_created, dcu.uploader, 1, 534, dcu.component, NULL
    FROM DistroComponentUploader as dcu
    WHERE component=7;
