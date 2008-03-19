SET client_min_messages=ERROR;

ALTER TABLE BranchSubscription
  ADD COLUMN review_level INT;

UPDATE BranchSubscription
SET review_level = 0
WHERE notification_level = 0;

UPDATE BranchSubscription
SET review_level = 1
WHERE review_level IS NULL;

ALTER TABLE BranchSubscription
  ALTER COLUMN review_level SET NOT NULL;

ALTER TABLE BranchSubscription
  ALTER COLUMN review_level SET DEFAULT 0;

-- Requested by sabdfl, a free-form string describing the vote
ALTER TABLE CodeReviewMessage
  ADD COLUMN vote_tag TEXT;

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

-- Need indexes for people merge
CREATE INDEX codereviewvote__registrant__idx ON CodeReviewVote(registrant);
CREATE INDEX codereviewvote__reviewer__idx ON CodeReviewVote(reviewer);

-- Indexes on foreign keys
CREATE INDEX codereviewvote__branch_merge_proposal__idx
    ON CodeReviewVote(branch_merge_proposal);
CREATE INDEX codereviewvote__vote_message__idx
    ON CodeReviewVote(vote_message);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 26, 0);
