SET client_min_messages=ERROR;

ALTER TABLE DistributionMirror ADD COLUMN status integer DEFAULT 10;
UPDATE DistributionMirror SET status = 10 -- PENDING_REVIEW
    WHERE official_candidate IS TRUE AND official_approved IS FALSE;
UPDATE DistributionMirror SET status = 20 -- UNOFFICIAL
    WHERE official_candidate IS FALSE;
UPDATE DistributionMirror SET status = 30 -- OFFICIAL
    WHERE official_candidate IS TRUE AND official_approved IS TRUE;
ALTER TABLE DistributionMirror ALTER COLUMN status SET NOT NULL;
ALTER TABLE DistributionMirror DROP COLUMN official_approved;

ALTER TABLE DistributionMirror 
    ADD COLUMN date_reviewed timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE DistributionMirror 
    ADD COLUMN reviewer integer REFERENCES Person(id);

ALTER TABLE MirrorDistroArchSeries RENAME COLUMN status TO freshness;
ALTER TABLE MirrorDistroSeriesSource RENAME COLUMN status TO freshness;

CREATE INDEX distributionmirror__country__status__idx
    ON DistributionMirror (country, status);
CREATE INDEX distributionmirror__status__idx
    ON DistributionMirror (status);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 55, 0);
