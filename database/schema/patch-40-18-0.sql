SET client_min_messages=ERROR;

CREATE INDEX mirrorproberecord__date_created__idx
    ON MirrorProbeRecord(date_created);

CREATE INDEX mirrorproberecord__distribution_mirror__idx
    ON MirrorProbeRecord(distribution_mirror);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 18, 0);

