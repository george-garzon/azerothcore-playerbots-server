-- Independent, quest-required creature drops only. Shared groups and references
-- are excluded so this cannot displace ordinary loot or affect container loot.
-- Keep original chances for idempotency and restoration. Do not drop this table.
CREATE TABLE IF NOT EXISTS custom_quest_drop_baseline (
    Entry INT UNSIGNED NOT NULL,
    Item INT UNSIGNED NOT NULL,
    OriginalChance FLOAT NOT NULL,
    PRIMARY KEY (Entry, Item)
) ENGINE=InnoDB;

START TRANSACTION;

INSERT IGNORE INTO custom_quest_drop_baseline (Entry, Item, OriginalChance)
SELECT Entry, Item, Chance
FROM creature_loot_template
WHERE QuestRequired = 1 AND Reference = 0 AND GroupId = 0
  AND Chance > 0 AND Chance < 100;

UPDATE creature_loot_template AS loot
JOIN custom_quest_drop_baseline AS baseline
  ON baseline.Entry = loot.Entry AND baseline.Item = loot.Item
SET loot.Chance = LEAST(100, baseline.OriginalChance * 2.5)
WHERE loot.QuestRequired = 1 AND loot.Reference = 0 AND loot.GroupId = 0
  AND loot.Chance = baseline.OriginalChance;

COMMIT;

SELECT COUNT(*) AS boosted_quest_drop_rows
FROM creature_loot_template AS loot
JOIN custom_quest_drop_baseline AS baseline
  ON baseline.Entry = loot.Entry AND baseline.Item = loot.Item
WHERE loot.QuestRequired = 1 AND loot.Reference = 0 AND loot.GroupId = 0
  AND loot.Chance = CAST(LEAST(100, baseline.OriginalChance * 2.5) AS FLOAT);
