SET client_min_messages=ERROR;

ALTER TABLE LaunchpadDatabaseRevision
    ADD CONSTRAINT launchpaddatabaserevision_pkey
    PRIMARY KEY(major, minor, patch);

INSERT INTO LaunchpadDatabaseRevision VALUES (10,0,0);

