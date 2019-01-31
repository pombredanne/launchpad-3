-- Copyright 2019 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- 0 == CHROOT
ALTER TABLE PocketChroot
    ADD COLUMN image_type integer DEFAULT 0 NOT NULL,
    ADD CONSTRAINT pocketchroot__distroarchseries__pocket__image_type__key
        UNIQUE (distroarchseries, pocket, image_type),
    DROP CONSTRAINT pocketchroot_distroarchrelease_key;

COMMENT ON COLUMN PocketChroot.image_type IS 'The type of this image.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 86, 0);
