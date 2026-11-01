-- Nova Station: database-backed job whitelist and trusted-player job playtime override.
CREATE TABLE IF NOT EXISTS `player_access_flags` (
  `ckey` varchar(32) NOT NULL,
  `head_job_whitelist` tinyint(1) NOT NULL DEFAULT 0,
  `job_playtime_override` tinyint(1) NOT NULL DEFAULT 0,
  `updated_by` varchar(32) NOT NULL DEFAULT '',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`ckey`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;