
UPDATE RequestedCDs SET quantityapproved = 0 WHERE quantityapproved IS NULL;
ALTER TABLE RequestedCDs ALTER COLUMN quantityapproved SET NOT NULL;

-- All existing standard requests are for the Ubuntu flavour.
UPDATE StandardShipItRequest SET flavour = 1;

ALTER TABLE StandardShipItRequest ALTER COLUMN flavour SET NOT NULL;
