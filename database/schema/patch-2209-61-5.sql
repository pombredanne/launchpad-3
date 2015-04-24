-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BranchMergeProposal ADD COLUMN source_git_repository integer REFERENCES gitrepository;
ALTER TABLE BranchMergeProposal ADD COLUMN source_git_path text;
ALTER TABLE BranchMergeProposal ADD COLUMN source_git_commit_sha1 character(40);
ALTER TABLE BranchMergeProposal ADD COLUMN target_git_repository integer REFERENCES gitrepository;
ALTER TABLE BranchMergeProposal ADD COLUMN target_git_path text;
ALTER TABLE BranchMergeProposal ADD COLUMN target_git_commit_sha1 character(40);
ALTER TABLE BranchMergeProposal ADD COLUMN dependent_git_repository integer REFERENCES gitrepository;
ALTER TABLE BranchMergeProposal ADD COLUMN dependent_git_path text;
ALTER TABLE BranchMergeProposal ADD COLUMN dependent_git_commit_sha1 character(40);

ALTER TABLE BranchMergeProposal
    ADD CONSTRAINT consistent_source_git_ref CHECK ((source_git_repository IS NULL) = (source_git_path IS NULL) AND (source_git_repository IS NULL) = (source_git_commit_sha1 IS NULL));
ALTER TABLE BranchMergeProposal
    ADD CONSTRAINT consistent_target_git_ref CHECK ((target_git_repository IS NULL) = (target_git_path IS NULL) AND (target_git_repository IS NULL) = (target_git_commit_sha1 IS NULL));
ALTER TABLE BranchMergeProposal
    ADD CONSTRAINT consistent_dependent_git_ref CHECK ((dependent_git_repository IS NULL) = (dependent_git_path IS NULL) AND (dependent_git_repository IS NULL) = (dependent_git_commit_sha1 IS NULL));

ALTER TABLE BranchMergeProposal
    ADD CONSTRAINT different_git_refs CHECK (source_git_repository IS NULL OR (ROW (source_git_repository, source_git_path) != ROW (target_git_repository, target_git_path) AND ROW (dependent_git_repository, dependent_git_path) != ROW (source_git_repository, source_git_path) AND ROW (dependent_git_repository, dependent_git_path) != ROW (target_git_repository, target_git_path)));

ALTER TABLE BranchMergeProposal ALTER COLUMN source_branch DROP NOT NULL;
ALTER TABLE BranchMergeProposal ALTER COLUMN target_branch DROP NOT NULL;
ALTER TABLE BranchMergeProposal
    ADD CONSTRAINT one_vcs CHECK (((source_branch IS NOT NULL AND target_branch IS NOT NULL) != (source_git_repository IS NOT NULL AND target_git_repository IS NOT NULL)) AND (dependent_branch IS NULL OR source_branch IS NOT NULL) AND (dependent_git_repository IS NULL OR source_git_repository IS NOT NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 5);
