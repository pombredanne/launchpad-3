SET client_min_messages=ERROR;

-- The BranchSubscription is missing a unique constraint.
-- A person should never be subscribed to a single branch more than once.

ALTER TABLE BranchSubscription
  ADD CONSTRAINT branchsubscription_unique_subscriber UNIQUE(person, branch);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 84, 0);

