SET client_min_messages=ERROR;

ALTER TABLE Language ADD COLUMN visible boolean;
UPDATE Language SET visible = False;
UPDATE Language SET visible = True WHERE code !~ '_';
UPDATE Language SET visible = False WHERE code = 'no';
UPDATE Language SET visible = True WHERE code IN
	('en_GB', 'en_AU', 'en_CA', 'pt_BR', 'zh_CN', 'zh_TW');
ALTER TABLE Language ALTER COLUMN visible SET NOT NULL;
DELETE FROM PersonLanguage WHERE language IN
	(SELECT id FROM Language WHERE visible = False);

INSERT INTO LaunchpadDatabaseRevision VALUES (17,4,0);

