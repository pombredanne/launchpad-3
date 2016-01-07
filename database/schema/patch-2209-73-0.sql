-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRecipeData
    ADD COLUMN base_git_repository integer REFERENCES GitRepository;
ALTER TABLE SourcePackageRecipeData
    ALTER COLUMN base_branch DROP NOT NULL;
ALTER TABLE SourcePackageRecipeData
    ADD CONSTRAINT one_base_vcs CHECK ((base_branch IS NOT NULL) != (base_git_repository IS NOT NULL));

COMMENT ON COLUMN SourcePackageRecipeData.base_git_repository IS 'The Git repository the recipe is based on.';

ALTER TABLE SourcePackageRecipeDataInstruction
    ADD COLUMN git_repository integer REFERENCES GitRepository;
ALTER TABLE SourcePackageRecipeDataInstruction
    ALTER COLUMN branch DROP NOT NULL;
ALTER TABLE SourcePackageRecipeDataInstruction
    ADD CONSTRAINT one_vcs CHECK ((branch IS NOT NULL) != (git_repository IS NOT NULL));

COMMENT ON COLUMN SourcePackageRecipeDataInstruction.git_repository IS 'The Git repository containing the branch being merged or nested.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 73, 0);
