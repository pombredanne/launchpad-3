SET client_min_messages=ERROR;

BEGIN TRANSACTION;

ALTER TABLE BranchMergeProposal ADD COLUMN conversation INTEGER;

CREATE TABLE CodeReviewSubscription (
    id SERIAL PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    person integer NOT NULL REFERENCES Person(id),
    date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
                 DEFAULT timezone('UTC'::text, now()),
    registrant INTEGER REFERENCES Person(id)
    );

CREATE TABLE CodeReviewMessage (
    id SERIAL PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    message INTEGER NOT NULL UNIQUE REFERENCES Message(id),
    vote INTEGER NOT NULL
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 90, 0);

COMMIT TRANSACTION;
