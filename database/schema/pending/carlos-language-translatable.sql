ALTER TABLE Language ADD translatable BOOLEAN;
ALTER TABLE Language ALTER COLUMN translatable SET DEFAULT TRUE;
UPDATE Language set translatable=TRUE;
ALTER TABLE Language ALTER COLUMN translatable SET NOT NULL;
