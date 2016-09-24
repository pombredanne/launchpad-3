-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

UPDATE product
    SET access_policies = (
        SELECT array_agg(AccessPolicy.id)
        FROM AccessPolicy
        WHERE
            AccessPolicy.product = Product.id
            AND AccessPolicy.type IN (5, 6)) -- PROPRIETARY, EMBARGOED
    WHERE information_type IN (5, 6);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 67, 2);
