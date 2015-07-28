-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

DROP INDEX livefsbuild__livefs__status__started__finished__created__id__idx;

CREATE INDEX livefsbuild__livefs__status__started__finished__created__id__idx
    ON LiveFSBuild (
        livefs, status, GREATEST(date_started, date_finished) DESC NULLS LAST,
        date_created DESC, id DESC);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 56, 1);
