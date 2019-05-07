-- Copyright 2019 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE UNIQUE INDEX productjob__job__key ON ProductJob (job);
CREATE INDEX snapbuild__build_request__idx ON SnapBuild (build_request);

INSERT INTO LaunchpadDatabaseRevision VALUES (2210, 01, 1);
