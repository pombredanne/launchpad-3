
/*
  Validate CVE numbers  
*/

ALTER TABLE CVERef ADD CONSTRAINT valid_cve CHECK (valid_cve(cveref));

UPDATE LaunchpadDatabaseRevision SET major=6, minor=22, patch=0;


