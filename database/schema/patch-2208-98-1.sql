-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE PackagingJob
  ADD COLUMN
    potemplate INTEGER DEFAULT NULL
      CONSTRAINT potemplate_fk REFERENCES POTemplate;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 98, 1);
