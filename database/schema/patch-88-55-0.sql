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

ALTER TABLE MirrorDistroArchSeries RENAME COLUMN status TO freshness;
ALTER TABLE MirrorDistroSeriesSource RENAME COLUMN status TO freshness;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 55, 0);
