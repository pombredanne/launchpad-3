set client_min_messages=ERROR;

ALTER TABLE Language ADD COLUMN direction integer;
ALTER TABLE Language ALTER COLUMN direction SET DEFAULT 0;
UPDATE Language SET direction = 0;
ALTER TABLE Language ALTER COLUMN direction SET NOT NULL;

/* The following languages are listed as RTL in the GTK+ po files,
 * so should cover the common languages.  Others language records
 * can be updated later.
 */
UPDATE Language set direction = 1
  WHERE code in ('ar', 'az', 'fa', 'he', 'yi');
UPDATE Language set direction = 1
  WHERE substring(code, 1, 3) in ('ar_', 'az_', 'fa_', 'he_', 'yi_');

INSERT INTO LaunchpadDatabaseRevision Values (25,33,0);
