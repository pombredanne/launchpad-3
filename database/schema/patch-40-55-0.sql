SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror 
    ADD CONSTRAINT valid_pulse_source CHECK (valid_absolute_url(pulse_source));

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 55, 0);
