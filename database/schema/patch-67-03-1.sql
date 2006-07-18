SET client_min_messages=ERROR;

ALTER TABLE DistroReleaseQueueBuild
    ADD CONSTRAINT distroreleasequeuebuild__distroreleasequeue__build__unique
    UNIQUE (distroreleasequeue, build);

CREATE INDEX distroreleasequeuebuild__build__idx
    ON DistroReleaseQueueBuild(build);

ALTER TABLE DistroReleaseQueueSource ADD CONSTRAINT
    distroreleasequeuesource__distroreleasequeue__sourcepackagerelease__unique
    UNIQUE (distroreleasequeue, sourcepackagerelease);

CREATE INDEX distroreleasequeuesource__sourcepackagerelease__idx
    ON DistroReleaseQueueSource(sourcepackagerelease);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 03, 1);

