
SET client_min_messages=ERROR;

ALTER TABLE DistroBounty RENAME TO DistributionBounty;

ALTER TABLE distrobounty_id_seq RENAME TO distributionbounty_id_seq;
ALTER TABLE DistributionBounty
    ALTER COLUMN id SET DEFAULT nextval('distributionbounty_id_seq');

ALTER TABLE DistributionBounty DROP CONSTRAINT distrobounty_pkey;
ALTER TABLE DistributionBounty
    ADD CONSTRAINT distributionbounty_pkey PRIMARY KEY (id);

ALTER TABLE DistributionBounty DROP CONSTRAINT distrobounty_bounty_key;
ALTER TABLE DistributionBounty
    ADD CONSTRAINT distributionbounty_bounty_distribution_uniq
    UNIQUE (bounty, distribution);

DROP INDEX distrobounty_distribution_idx;
CREATE INDEX distributionbounty_distribution_idx
    ON DistributionBounty(distribution);

ALTER TABLE DistributionBounty
    ADD CONSTRAINT distributionbounty_distribution_fk
    FOREIGN KEY (distribution) REFERENCES Distribution(id);
ALTER TABLE DistributionBounty DROP CONSTRAINT distrobounty_distribution_fk;

ALTER TABLE DistributionBounty
    ADD CONSTRAINT distributionbounty_bounty_fk
    FOREIGN KEY (bounty) REFERENCES Bounty(id);
ALTER TABLE DistributionBounty DROP CONSTRAINT distrobounty_bounty_fk;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 48, 0);
