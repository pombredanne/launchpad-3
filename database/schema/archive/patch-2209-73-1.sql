-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

DROP INDEX sourcepackagerecipebuild__recipe__started__finished__created__idx;
DROP INDEX sourcepackagerecipebuild__recipe__started__finished__idx;

CREATE INDEX sourcepackagerecipebuild__recipe__started__finished__created__idx
    ON SourcePackageRecipeBuild (
        recipe, GREATEST(date_started, date_finished) DESC NULLS LAST,
        date_created DESC, id DESC);
CREATE INDEX sourcepackagerecipebuild__recipe__started__finished__idx
    ON SourcePackageRecipeBuild (
        recipe, GREATEST(date_started, date_finished) DESC NULLS LAST,
        id DESC);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 73, 1);
