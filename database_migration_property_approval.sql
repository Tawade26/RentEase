-- Migration: Add approval system to properties table
-- Run this SQL script to update the database schema

-- Check if columns already exist before adding
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'properties' 
AND COLUMN_NAME = 'status';

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `properties` 
     ADD COLUMN `status` ENUM(''pending'', ''approved'', ''rejected'') DEFAULT ''pending'' AFTER `date_posted`,
     ADD COLUMN `approved_by` INT(11) DEFAULT NULL AFTER `status`,
     ADD COLUMN `approved_at` DATETIME DEFAULT NULL AFTER `approved_by`,
     ADD KEY `idx_properties_status` (`status`)',
    'SELECT ''Columns already exist'' AS message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add foreign key constraint if it doesn't exist
SET @fk_exists = 0;
SELECT COUNT(*) INTO @fk_exists
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'properties'
AND CONSTRAINT_NAME = 'properties_approved_by_fk';

SET @sql2 = IF(@fk_exists = 0,
    'ALTER TABLE `properties`
     ADD CONSTRAINT `properties_approved_by_fk` FOREIGN KEY (`approved_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL',
    'SELECT ''Foreign key already exists'' AS message');

PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- Update existing properties to approved status (important: this makes them visible)
UPDATE `properties` 
SET `status` = 'approved', 
    `approved_at` = COALESCE(`approved_at`, `date_posted`)
WHERE `status` IS NULL OR `status` = 'pending';

