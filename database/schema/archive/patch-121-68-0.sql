SET client_min_messages=ERROR;

ALTER TABLE CodeReviewVote
    ADD CONSTRAINT codereviewvode__reviewer__branch_merge_proposal__key
    UNIQUE (reviewer, branch_merge_proposal);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 68, 0);

