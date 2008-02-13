SET client_min_messages=ERROR;

ALTER TABLE BranchSubscription
  ADD COLUMN review_level INT;

UPDATE BranchSubscription
SET review_level = 0
WHERE notification_level = 0;

UPDATE BranchSubscription
SET review_level = 1
WHERE notification_level IS NULL;

ALTER TABLE BranchSubscription
  ALTER COLUMN review_level SET NOT NULL;

ALTER TABLE BranchSubscription
  ALTER COLUMN review_level SET DEFAULT 0;

CREATE TABLE CodeReviewMessage (
-- CodeReviewMessage does not need a date_created, because it's always created
-- at the same time as a Message, which has one.
    id SERIAL PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    message INTEGER NOT NULL UNIQUE REFERENCES Message(id),
    vote INTEGER
    );

ALTER TABLE BranchMergeProposal
    ADD COLUMN conversation INTEGER REFERENCES CodeReviewMessage;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
