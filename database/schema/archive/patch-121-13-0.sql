SET client_min_messages=ERROR;

-- CREATE TABLE CodeReviewSubscription (
--     id SERIAL PRIMARY KEY,
--     branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
--     person INTEGER NOT NULL REFERENCES Person(id),
--     date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
--                  DEFAULT timezone('UTC'::text, now()),
--     registrant INTEGER REFERENCES Person(id)
--     );
-- 
-- -- Need indexes for people merge
-- CREATE INDEX codereviewsubscription__registrant__idx
--   ON CodeReviewSubscription(registrant);
-- CREATE INDEX codereviewsubscription__person__idx
--   ON CodeReviewSubscription(person);

CREATE TABLE CodeReviewMessage (
-- CodeReviewMessage does not need a date_created, because it's always created
-- at the same time as a Message, which has one.
    id SERIAL PRIMARY KEY,
    branch_merge_proposal INTEGER NOT NULL REFERENCES BranchMergeProposal(id),
    message INTEGER NOT NULL UNIQUE REFERENCES Message(id),
    vote INTEGER,
    -- Index to allow quick ordering of all messages for a proposal and
    -- to select the initial message in the conversation.
    CONSTRAINT codereviewmessage__branch_merge_proposal__id_key
        UNIQUE (branch_merge_proposal, id)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 13, 0);
