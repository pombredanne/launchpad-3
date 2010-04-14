-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Add a column to track when the project was confirmed to not be packaged
-- in Ubuntu. The default is NULL, meaning no one has ever confirmed the
-- current packaging.
ALTER TABLE Product
    ADD COLUMN date_last_packaging_check timestamp without time zone;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 96, 0);
