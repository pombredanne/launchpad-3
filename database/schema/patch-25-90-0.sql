set client_min_messages=ERROR;

ALTER TABLE Language ADD COLUMN direction integer NOT NULL DEFAULT 0;

/* The following languages are listed as RTL in the GTK+ po files,
 * so should cover the common languages.  Others language records
 * can be updated later.
 */
UPDATE Language set direction = 1
  WHERE code in ('ar', 'az', 'fa', 'he', 'yi');
UPDATE Language set direction = 1
  WHERE substring(code, 1, 3) in ('ar_', 'az_', 'fa_', 'he_', 'yi_');

INSERT INTO LaunchpadDatabaseRevision Values (25,90,0);
