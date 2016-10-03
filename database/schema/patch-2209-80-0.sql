-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitRepository ADD COLUMN repository_type integer;

COMMENT ON COLUMN GitRepository.repository_type IS 'Repositories are currently one of HOSTED (1) or IMPORTED (3).';

ALTER TABLE CodeImport
    ADD COLUMN git_repository integer REFERENCES gitrepository,
    ALTER COLUMN branch DROP NOT NULL,
    ADD CONSTRAINT one_target_vcs CHECK (
        (branch IS NOT NULL) != (git_repository IS NOT NULL)),
    ADD CONSTRAINT valid_source_target_vcs_pairing CHECK (
        branch IS NOT NULL OR rcs_type = 4),
    DROP CONSTRAINT codeimport_branch_key;

COMMENT ON COLUMN CodeImport.branch IS 'The Bazaar branch produced by the import system, if applicable.  A placeholder branch is created when the import is created.  The import is associated with a target through the branch.';
COMMENT ON COLUMN CodeImport.git_repository IS 'The Git repository produced by the import system, if applicable.  A placeholder repository is created when the import is created.  The import is associated with a target through the repository.';

CREATE UNIQUE INDEX codeimport__branch__key
    ON CodeImport(branch) WHERE branch IS NOT NULL;
CREATE UNIQUE INDEX codeimport__git_repository__key
    ON CodeImport(git_repository) WHERE git_repository IS NOT NULL;

ALTER TABLE CodeImportJob ADD COLUMN secret text;

COMMENT ON COLUMN CodeImportJob.secret IS 'A secret token used to communicate with the code hosting service.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 80, 0);
