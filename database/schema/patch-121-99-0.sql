SET client_min_messages=ERROR;

-- Replace the simple uniqueness constraint for HWVendorName.name
-- by a Unicode-aware lower-case uniqueness constraint.

ALTER TABLE HWVendorName DROP CONSTRAINT hwvendorname_name_key;
CREATE UNIQUE INDEX hwvendorname__lc_vendor_name__idx ON HWVendorName(ulower(name));

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
