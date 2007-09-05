
-- The branch puller logic has changed. Instead of using widely different
-- queries for different types of branches, the puller now only mirrors
-- branches that have a mirror_request_time that is not NULL and in the past.
-- We need to migrate the existing branches over so they will work with the new
-- puller.

-- HOSTED branches were mirrored when last_mirror_attempt was six hours in the
-- past or when a mirror had been requested. The equivalent for the former is a
-- mirror_request_time set six hours after last_mirror_attempt.
UPDATE Branch
SET mirror_request_time = last_mirror_attempt + '6 hours'
WHERE last_mirror_attempt IS NOT NULL
AND mirror_request_time IS NULL
AND branch_type = 1;

-- If a HOSTED or MIRRORED branch has never been mirrored, nor had a mirror
-- requested then it should be mirrored on the next run. Set the
-- mirror_request_time to NOW.
UPDATE Branch
SET mirror_request_time = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
WHERE last_mirror_attempt IS NULL
AND mirror_request_time IS NULL
AND branch_type IN (1, 2);

-- MIRRORED branches were mirrored when last_mirror_attempt was six hours in
-- the past. The equivalent is a mirror_request_time set six hours after
-- last_mirror_attempt.
UPDATE Branch
SET mirror_request_time = last_mirror_attempt + '6 hours'
WHERE last_mirror_attempt IS NOT NULL
AND branch_type = 2;

-- IMPORTED branches were mirrored when datelastsynced was more recent than the
-- last mirror attempt. Now we update mirror_request_time on sync.
UPDATE Branch
SET mirror_request_time = ProductSeries.datelastsynced
FROM ProductSeries
WHERE branch_type = 3
AND ProductSeries.import_branch = Branch.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 45, 0);
