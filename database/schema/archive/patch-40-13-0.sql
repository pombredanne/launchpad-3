SET client_min_messages=ERROR;

CREATE TABLE DistributionMirror(
    id                  serial PRIMARY KEY,
    distribution        integer NOT NULL REFERENCES Distribution(id),
    name                text UNIQUE NOT NULL
        CONSTRAINT valid_name CHECK (valid_name(name)),
    http_base_url       text UNIQUE CONSTRAINT valid_http_base_url
                                    CHECK (valid_absolute_url(http_base_url)),
    ftp_base_url        text UNIQUE CONSTRAINT valid_ftp_base_url
                                    CHECK (valid_absolute_url(ftp_base_url)),
    rsync_base_url      text UNIQUE CONSTRAINT valid_rsync_base_url
                                    CHECK (valid_absolute_url(rsync_base_url)),
    displayname         text,
    description         text,
    owner               integer NOT NULL REFERENCES Person(id),
    speed               integer NOT NULL,
    country             integer NOT NULL REFERENCES Country(id),
    content             integer NOT NULL,
    file_list           integer REFERENCES LibraryFileAlias(id),
    official_candidate  boolean NOT NULL DEFAULT false,
    official_approved   boolean NOT NULL DEFAULT false,
    enabled             boolean NOT NULL DEFAULT false,
    pulse_type          integer NOT NULL,
    pulse_source        text,
    CONSTRAINT one_or_more_urls CHECK (
        http_base_url IS NOT NULL OR ftp_base_url IS NOT NULL OR
        rsync_base_url IS NOT NULL
        ),
    CONSTRAINT has_pulse_source CHECK (
        pulse_type <> 1 OR pulse_source IS NOT NULL
        )
);

CREATE TABLE MirrorDistroArchRelease(
    id                  serial PRIMARY KEY,
    distribution_mirror integer NOT NULL REFERENCES DistributionMirror(id),
    distro_arch_release integer NOT NULL REFERENCES DistroArchRelease(id),
    status              integer NOT NULL,
    pocket              integer NOT NULL
);

CREATE TABLE MirrorDistroReleaseSource(
    id                  serial PRIMARY KEY,
    distribution_mirror integer NOT NULL REFERENCES DistributionMirror(id),
    distro_release      integer NOT NULL REFERENCES DistroRelease(id),
    status              integer NOT NULL
);

CREATE TABLE MirrorProbeRecord(
    id                  serial PRIMARY KEY,
    distribution_mirror integer NOT NULL REFERENCES DistributionMirror(id),
    log_file            integer NOT NULL REFERENCES LibraryFileAlias(id),
    date_created        timestamp without time zone NOT NULL
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 13, 0);
