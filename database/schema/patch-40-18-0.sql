SET client_min_messages=ERROR;

CREATE INDEX mirrorproberecord__date_created__idx
    ON MirrorProbeRecord(date_created);

CREATE INDEX mirrorproberecord__distribution_mirror__idx
    ON MirrorProbeRecord(distribution_mirror);

DROP INDEX person_sorting_idx;

CREATE INDEX person_sorting_idx ON Person(person_sort_key(displayname, name));

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 18, 0);

