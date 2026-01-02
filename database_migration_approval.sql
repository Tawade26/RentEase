-- Migration: Add approval system to users table
-- Run this SQL script to update the database schema

ALTER TABLE `users` 
ADD COLUMN `status` ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' AFTER `role`,
ADD COLUMN `role_change_request` ENUM('tenant', 'owner', NULL) DEFAULT NULL AFTER `status`,
ADD COLUMN `approved_by` INT(11) DEFAULT NULL AFTER `role_change_request`,
ADD COLUMN `approved_at` DATETIME DEFAULT NULL AFTER `approved_by`,
ADD KEY `idx_users_status` (`status`),
ADD CONSTRAINT `users_approved_by_fk` FOREIGN KEY (`approved_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

-- Update existing users to approved status (except admin)
UPDATE `users` SET `status` = 'approved', `approved_at` = `date_registered` WHERE `status` IS NULL;

-- Set admin user as approved
UPDATE `users` SET `status` = 'approved' WHERE `role` = 'admin';

