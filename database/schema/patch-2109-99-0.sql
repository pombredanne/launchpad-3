SET client_min_messages=ERROR;

CREATE VIEW HWDriverPackageNames AS
    SELECT DISTINCT ON (package_name) id, package_name from HWDriver
        ORDER BY package_name, id;

CREATE VIEW HWDriverNames AS
    SELECT DISTINCT ON (name) id, name from HWDriver
        ORDER BY name, id;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
