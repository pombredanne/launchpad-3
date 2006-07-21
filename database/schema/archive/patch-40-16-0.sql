SET client_min_messages=ERROR;

CREATE VIEW BinaryAndSourcePackageNameView AS
    SELECT name FROM BinaryPackageName
    
    UNION

    SELECT name FROM SourcePackageName
;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 16, 0);

