SET client_min_messages=error;

ALTER TABLE MirrorDistroReleaseSource 
    RENAME COLUMN distro_release to distrorelease;

CREATE TABLE MirrorCDImageDistroRelease (
    id SERIAL PRIMARY KEY,
    distribution_mirror integer NOT NULL REFERENCES DistributionMirror(id),
    distrorelease       integer NOT NULL REFERENCES DistroRelease(id),
    flavour             text NOT NULL
);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 80, 0);
