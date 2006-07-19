SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror ADD CONSTRAINT valid_pulse_source
    CHECK (valid_absolute_url(pulse_source));

ALTER TABLE MirrorDistroReleaseSource ADD COLUMN pocket integer;
UPDATE MirrorDistroReleaseSource SET pocket=0;
ALTER TABLE MirrorDistroReleaseSource ALTER COLUMN pocket SET NOT NULL;

ALTER TABLE MirrorDistroReleaseSource ADD COLUMN component integer;
ALTER TABLE MirrorDistroReleaseSource
    ADD CONSTRAINT mirrordistroreleasesource__component__fk 
    FOREIGN KEY (component) REFERENCES Component;

ALTER TABLE MirrorDistroArchRelease ADD COLUMN component integer;
ALTER TABLE MirrorDistroArchRelease
    ADD CONSTRAINT mirrordistroarchrelease__component__fk 
    FOREIGN KEY (component) REFERENCES Component;

ALTER TABLE MirrorProbeRecord ALTER COLUMN log_file DROP NOT NULL;

CREATE UNIQUE INDEX componentselection__distrorelease__component__uniq ON
    ComponentSelection (distrorelease, component);

CREATE UNIQUE INDEX mirrordistroreleasesource_uniq ON MirrorDistroReleaseSource 
    (distribution_mirror, distro_release, component, pocket);

CREATE UNIQUE INDEX mirrordistroarchrelease_uniq ON MirrorDistroArchRelease
    (distribution_mirror, distro_arch_release, component, pocket);


DROP INDEX mirrorproberecord__distribution_mirror__idx;
CREATE INDEX mirrorproberecord__distribution_mirror__date_created__idx
    ON MirrorProbeRecord(distribution_mirror, date_created);
CREATE INDEX mirrorproberecord__log_file__idx
    ON MirrorProbeRecord(log_file) WHERE log_file IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 22, 0);
