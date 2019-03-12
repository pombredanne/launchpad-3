-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Snap
    ADD COLUMN git_repository_url text,
    DROP CONSTRAINT consistent_git_ref,
    ADD CONSTRAINT consistent_git_ref CHECK (((git_repository IS NULL) AND (git_repository_url IS NULL)) = (git_path IS NULL)),
    DROP CONSTRAINT consistent_vcs,
    ADD CONSTRAINT consistent_vcs CHECK (null_count(ARRAY[branch, git_repository, octet_length(git_repository_url)]) >= 2),
    ADD CONSTRAINT valid_git_repository_url CHECK (valid_absolute_url(git_repository_url));

COMMENT ON COLUMN Snap.git_repository_url IS 'A URL to a Git repository with a branch containing a snap recipe.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 7);
