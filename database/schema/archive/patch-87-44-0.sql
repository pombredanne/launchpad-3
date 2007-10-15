SET client_min_messages=ERROR;

-- 1: HOSTED
-- 2: MIRRORED
-- 3: IMPORTED
-- 4: REMOTE

ALTER TABLE Branch DROP CONSTRAINT branch_type_url_consistent;

-- URLs are optional for remote branches.

ALTER TABLE Branch ADD CONSTRAINT branch_type_url_consistent
CHECK ((branch_type = 2 AND url IS NOT NULL) OR
       (branch_type in (1,3) AND url IS NULL) OR
       (branch_type = 4));

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 44, 0);

