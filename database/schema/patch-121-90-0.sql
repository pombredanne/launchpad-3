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


ALTER TABLE BranchMergeProposal
    ADD COLUMN conversation INTEGER REFERENCES CodeReviewMessage;


CREATE TABLE CodeReviewVote (
    id SERIAL PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    reviewer INTEGER NOT NULL REFERENCES Person(id),
    review_type TEXT,
    registrant INTEGER NOT NULL REFERENCES Person(id),
    vote_message INTEGER REFERENCES CodeReviewMessage(id),
    date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
      DEFAULT timezone('UTC'::text, now())
    );


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
