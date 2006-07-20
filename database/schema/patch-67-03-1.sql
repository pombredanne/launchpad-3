SET client_min_messages=ERROR;

/*
Daniel Silverstone (Kinnison): I'm not so convinced about the new constraints
Daniel Silverstone (Kinnison): In particular, if the queue is to be used to model packages getting into derivatives (which makes sense) then we can't have the constraint
stub: Can we keep it until then?
Daniel Silverstone (Kinnison): stub: sure, constraints can always be relaxed
*/

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

