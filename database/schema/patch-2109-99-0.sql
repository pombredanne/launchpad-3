SET client_min_messages=ERROR;

alter table codereviewvote
  drop constraint codereviewvode__reviewer__branch_merge_proposal__key;

alter table codereviewvote
  add constraint codereviewvote__reviewer__branch_merge_proposal__key
    unique(branch_merge_proposal, reviewer, review_type);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
