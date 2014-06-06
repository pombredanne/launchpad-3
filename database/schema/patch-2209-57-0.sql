-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE builder
    ADD COLUMN clean_status integer,
    ADD COLUMN vm_reset_protocol integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 57, 0);
