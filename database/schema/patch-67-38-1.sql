SET client_min_messages=ERROR;

-- BranchSubscription alterations

ALTER TABLE branchsubscription ADD COLUMN notification_level int4 NOT NULL DEFAULT(1);
ALTER TABLE branchsubscription ADD COLUMN max_diff_lines int4;

-- dbschema enum class for notification_level
--  0 := no email
--  1 := branch attribute notifications only
--  2 := branch diff notifications only
--  3 := both diffs, and attribute notifications


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 38, 1);

