-- Set questionownersolved karma to 0 points.
-- Workflow changes make this a required step, devaluing it.
UPDATE KarmaAction
SET points = 0
WHERE name = 'questionownersolved'