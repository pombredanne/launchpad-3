SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror 
    ADD CONSTRAINT valid_pulse_source CHECK (valid_absolute_url(pulse_source));

ALTER TABLE MirrorDistroReleaseSource ADD COLUMN pocket integer;
ALTER TABLE MirrorDistroReleaseSource ALTER COLUMN pocket SET NOT NULL;

ALTER TABLE MirrorDistroReleaseSource ADD COLUMN component integer;
ALTER TABLE MirrorDistroReleaseSource ADD CONSTRAINT component_fk 
    FOREIGN KEY (component) REFERENCES Component;

ALTER TABLE MirrorDistroArchRelease ADD COLUMN component integer;
ALTER TABLE MirrorDistroArchRelease ADD CONSTRAINT component_fk 
    FOREIGN KEY (component) REFERENCES Component;

ALTER TABLE MirrorProbeRecord ALTER COLUMN log_file DROP NOT NULL;

CREATE UNIQUE INDEX component_distrorelease_uniq ON
    ComponentSelection USING btree (component, distrorelease);

CREATE UNIQUE INDEX mirror_release_component_pocket_uniq ON
    MirrorDistroReleaseSource 
    USING btree (distribution_mirror, distro_release, component, pocket);

CREATE UNIQUE INDEX mirror_arch_release_component_pocket_uniq ON
    MirrorDistroArchRelease 
    USING btree (distribution_mirror, distro_arch_release, component, pocket);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 55, 0);
