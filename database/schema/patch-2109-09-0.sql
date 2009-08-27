-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE CodeReviewVote
  DROP constraint codereviewvode__reviewer__branch_merge_proposal__key;

CREATE UNIQUE INDEX codereviewvote__branch_merge_proposal__reviewer__key
    ON CodeReviewVote(branch_merge_proposal, reviewer)
    WHERE review_type IS NULL;

CREATE UNIQUE INDEX
    codereviewvote__branch_merge_proposal__reviewer__review_type__key
    ON CodeReviewVote(branch_merge_proposal, reviewer, review_type)
    WHERE review_type IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 9, 0);
