-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BinaryPackageBuild ADD COLUMN external_dependencies text;

COMMENT ON COLUMN BinaryPackageBuild.external_dependencies IS 'Newline-separated list of repositories to be used to retrieve any external build dependencies when performing this build, in the format: "deb http[s]://[user:pass@]<host>[/path] series[-pocket] [components]".  This is intended for bootstrapping build-dependency loops.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 72, 0);
