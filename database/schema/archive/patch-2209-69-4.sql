-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Snap
    ADD COLUMN auto_build boolean DEFAULT false NOT NULL,
    ADD COLUMN auto_build_archive integer REFERENCES archive,
    ADD COLUMN auto_build_pocket integer,
    ADD COLUMN is_stale boolean DEFAULT true NOT NULL,
    ADD CONSTRAINT consistent_auto_build CHECK (NOT auto_build OR (auto_build_archive IS NOT NULL AND auto_build_pocket IS NOT NULL));

COMMENT ON COLUMN Snap.auto_build IS 'Whether this snap is built automatically when the branch containing its snap recipe changes.';
COMMENT ON COLUMN Snap.auto_build_archive IS 'The archive that automatic builds of this snap package should build from.';
COMMENT ON COLUMN Snap.auto_build_pocket IS 'The pocket that automatic builds of this snap package should build from.';
COMMENT ON COLUMN Snap.is_stale IS 'True if this snap package has not been built since a branch was updated.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 4);
