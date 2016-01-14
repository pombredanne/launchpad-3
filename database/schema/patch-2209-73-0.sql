-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Snap privacy model is based only on ownership, similarly to Archives.
ALTER TABLE Snap ADD COLUMN private boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN Snap.private IS 'Whether or not this snap is only visible to owners.';

CREATE INDEX snap__private__idx ON snap USING btree (private);


-- Copying original snap branch references to SnapBuild on creation, this way
-- we can accurately calculate permission on builds after snap changes. 
ALTER TABLE SnapBuild ADD COLUMN branch integer REFERENCES Branch;
ALTER TABLE SnapBuild ADD COLUMN git_repository integer REFERENCES GitRepository;
ALTER TABLE SnapBuild ADD COLUMN git_path text;
ALTER TABLE SnapBuild ADD CONSTRAINT consistent_git_ref
    CHECK ((git_repository IS NULL) = (git_path IS NULL));

COMMENT ON COLUMN SnapBuild.branch IS 'Copied from Snap.branch on creation.';
COMMENT ON COLUMN SnapBuild.git_repository IS 'Copied from Snap.git_repository on creation.';
COMMENT ON COLUMN SnapBuild.git_path IS 'Copied from Snap.git_path on creation.';

CREATE INDEX snapbuild__branch__idx ON SnapBuild (branch);
CREATE INDEX snapbuild__git_repository__idx ON SnapBuild (git_repository);


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 73, 0);
