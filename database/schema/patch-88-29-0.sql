SET client_min_messages=ERROR;

-- Controlling PPA support.
ALTER TABLE DistroArchSeries ADD COLUMN ppa_supported boolean
    DEFAULT FALSE NOT NULL;

-- Explicitly storing the virtual machine hostname for each builder.
ALTER TABLE Builder ADD COLUMN vm_host text;

-- Storing build ETA on creation.
ALTER TABLE Build ADD COLUMN estimated_build_duration interval;
ALTER TABLE Build ADD COLUMN build_warnings text;


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 29, 0);
