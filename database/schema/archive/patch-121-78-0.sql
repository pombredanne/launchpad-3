SET client_min_messages=ERROR;

ALTER TABLE BranchMergeProposal
    ADD COLUMN root_message_id text;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 78, 0);
