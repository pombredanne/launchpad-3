SET client_min_messages=ERROR;

CREATE TABLE CodeReviewTask(
    id serial PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
            DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    registrant INTEGER NOT NULL REFERENCES Person(id),
    reviewer INTEGER NOT NULL REFERENCES Person(id)
    );

CREATE INDEX codereviewtask__branch_merge_proposal__idx
    ON CodeReviewTask(branch_merge_proposal);

CREATE INDEX codereviewtask__registrant__idx ON CodeReviewTask(registrant);

CREATE INDEX codereviewtask__reviewer__idx ON CodeReviewTask(reviewer);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 18, 0);
