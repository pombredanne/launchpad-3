-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Processor
    ADD COLUMN build_by_default boolean DEFAULT false NOT NULL,
    ADD COLUMN supports_nonvirtualized boolean DEFAULT true NOT NULL,
    ADD COLUMN supports_virtualized boolean DEFAULT false NOT NULL;

ALTER TABLE Processor
    ADD CONSTRAINT restricted_not_default
        CHECK (NOT restricted OR NOT build_by_default);

UPDATE processor SET supports_virtualized = true
    WHERE name IN ('i386', 'amd64', 'arm64', 'armhf', 'lpia', '386');

UPDATE processor SET build_by_default = true
    WHERE name IN ('i386', 'amd64', 'lpia', '386');

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 64, 0);
