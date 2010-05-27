-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;
ALTER TABLE SourcePackageRecipe ADD COLUMN is_stale BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE SourcePackageRecipeBuild ADD COLUMN manifest INTEGER REFERENCES SourcePackageRecipeData;
INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
