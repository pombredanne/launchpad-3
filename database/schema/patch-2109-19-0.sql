SET client_min_messages=ERROR;

ALTER TABLE RequestedCDs
    ADD CONSTRAINT requestedcds_unique_distroseries_arch_and_flavour
    UNIQUE (request, distroseries, architecture, flavour);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 19, 0);
