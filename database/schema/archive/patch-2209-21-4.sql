SET client_min_messages = ERROR;

-- This patch originally added update_database_disk_utilization(), but
-- it failed to apply on PostgreSQL >=9.5. It has been replaced with a
-- more compatible version in 2209-81-0. Deleting history is gross, but
-- we can get away without properly altering it.

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 21, 4);
