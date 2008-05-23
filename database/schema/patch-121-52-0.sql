SET client_min_messages=ERROR;

DROP INDEX archive__owner__key;

-- The 'owner' FK will be made mandatory. Set the owner for archive
-- rows which do not have one.
UPDATE archive SET owner = distribution.owner FROM distribution
WHERE archive.distribution = distribution.id AND archive.owner IS NULL;

ALTER TABLE archive ALTER COLUMN owner SET NOT NULL;

DROP INDEX archive__distribution__purpose__key;
-- We only allow one archive per distribution for primary and partner
-- archive purposes.
CREATE UNIQUE INDEX archive__distribution__purpose__key
    ON Archive (distribution, purpose) WHERE purpose IN (1,4);

-- An archive name column is added in order to facilitate multiple PPAs
-- per owner (and also "rebuild archives")
ALTER TABLE archive ADD COLUMN name Text NOT NULL Default 'default';
ALTER TABLE archive ADD CONSTRAINT valid_name CHECK (valid_name(name));

UPDATE archive SET name='primary' WHERE purpose=1;
UPDATE archive SET name='embargoed' WHERE purpose=3;
UPDATE archive SET name='partner' WHERE purpose=4;
UPDATE archive SET name='obsolete' WHERE purpose=5;
CREATE UNIQUE INDEX archive__owner__key ON Archive (owner, distribution, name);

-- A user may or may not be interested in publishing the (rebuild) archive.
-- This can be controlled via the boolean 'publish' column introduced below.
ALTER TABLE archive ADD COLUMN publish Boolean NOT NULL Default True;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 52, 0);
