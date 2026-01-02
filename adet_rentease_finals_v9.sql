-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Generation Time: Jan 02, 2026 at 05:46 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `adet_rentease`
--

-- --------------------------------------------------------

--
-- Table structure for table `analytics_events`
--

CREATE TABLE `analytics_events` (
  `event_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `event_type` varchar(50) NOT NULL,
  `property_id` int(11) DEFAULT NULL,
  `room_id` int(11) DEFAULT NULL,
  `booking_id` int(11) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `audit_logs`
--

CREATE TABLE `audit_logs` (
  `log_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `table_name` varchar(50) DEFAULT NULL,
  `record_id` int(11) DEFAULT NULL,
  `old_values` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`old_values`)),
  `new_values` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`new_values`)),
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `bookings`
--

CREATE TABLE `bookings` (
  `booking_id` int(11) NOT NULL,
  `tenant_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `status` enum('pending','approved','rejected','cancelled','completed') DEFAULT 'pending',
  `created_at` datetime DEFAULT current_timestamp(),
  `deleted_at` datetime DEFAULT NULL
) ;

--
-- Dumping data for table `bookings`
--

INSERT INTO `bookings` (`booking_id`, `tenant_id`, `room_id`, `start_date`, `end_date`, `status`, `created_at`, `deleted_at`) VALUES
(1, 5, 1, '2026-01-01', '2026-12-31', 'approved', '2026-01-01 23:27:34', NULL),
(2, 9, 3, '2026-01-05', '2026-06-30', 'approved', '2026-01-01 23:27:34', NULL),
(3, 10, 3, '2026-01-05', '2026-06-30', 'approved', '2026-01-01 23:27:34', NULL),
(4, 11, 3, '2026-01-10', '2026-06-30', 'rejected', '2026-01-01 23:27:34', NULL),
(5, 12, 3, '2026-01-12', '2026-06-30', 'approved', '2026-01-01 23:27:34', NULL),
(6, 13, 4, '2026-02-01', '2027-02-01', 'approved', '2026-01-01 23:27:34', NULL),
(7, 14, 4, '2026-02-01', '2027-02-01', 'cancelled', '2026-01-01 23:27:34', NULL),
(8, 15, 5, '2026-01-15', '2026-12-15', 'approved', '2026-01-01 23:27:34', NULL),
(9, 16, 6, '2026-03-01', '2027-03-01', 'pending', '2026-01-01 23:27:34', NULL),
(10, 17, 8, '2026-01-20', '2026-07-20', 'approved', '2026-01-01 23:27:34', NULL),
(11, 19, 8, '2026-01-20', '2026-07-20', 'rejected', '2026-01-01 23:27:34', NULL),
(12, 20, 9, '2026-01-02', NULL, 'approved', '2026-01-02 19:18:40', NULL);

--
-- Triggers `bookings`
--
DELIMITER $$
CREATE TRIGGER `log_booking_status_change` AFTER UPDATE ON `bookings` FOR EACH ROW BEGIN
  IF NEW.status != OLD.status THEN
    INSERT INTO booking_history (booking_id, status_changed_to, changed_by, changed_at)
    VALUES (NEW.booking_id, NEW.status, NEW.tenant_id, NOW());
  END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `update_room_tenants_on_approval` AFTER UPDATE ON `bookings` FOR EACH ROW BEGIN
  IF NEW.status = 'approved' AND OLD.status != 'approved' THEN
    UPDATE rooms 
    SET current_tenants = current_tenants + 1,
        available_tenants = available_tenants - 1
    WHERE room_id = NEW.room_id;
  END IF;
  
  IF NEW.status IN ('cancelled', 'rejected') AND OLD.status = 'approved' THEN
    UPDATE rooms 
    SET current_tenants = GREATEST(0, current_tenants - 1),
        available_tenants = available_tenants + 1
    WHERE room_id = NEW.room_id;
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `booking_history`
--

CREATE TABLE `booking_history` (
  `history_id` int(11) NOT NULL,
  `booking_id` int(11) NOT NULL,
  `status_changed_to` enum('pending','approved','rejected','cancelled','completed') DEFAULT NULL,
  `changed_by` int(11) DEFAULT NULL,
  `change_reason` text DEFAULT NULL,
  `changed_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `booking_history`
--

INSERT INTO `booking_history` (`history_id`, `booking_id`, `status_changed_to`, `changed_by`, `change_reason`, `changed_at`) VALUES
(1, 1, 'approved', 5, NULL, '2026-01-01 23:27:34'),
(2, 2, 'approved', 9, NULL, '2026-01-01 23:27:34'),
(3, 3, 'approved', 10, NULL, '2026-01-01 23:27:34'),
(4, 6, 'approved', 13, NULL, '2026-01-01 23:27:34'),
(5, 8, 'approved', 15, NULL, '2026-01-01 23:27:34'),
(6, 10, 'approved', 17, NULL, '2026-01-01 23:27:34'),
(7, 7, 'cancelled', 14, NULL, '2026-01-01 23:27:34'),
(8, 11, 'rejected', 19, NULL, '2026-01-01 23:27:34'),
(9, 12, 'approved', 20, NULL, '2026-01-02 19:35:10'),
(10, 4, 'rejected', 11, NULL, '2026-01-02 19:35:39'),
(11, 5, 'approved', 12, NULL, '2026-01-02 19:35:44');

-- --------------------------------------------------------

--
-- Table structure for table `lease_agreements`
--

CREATE TABLE `lease_agreements` (
  `agreement_id` int(11) NOT NULL,
  `booking_id` int(11) NOT NULL,
  `document_url` varchar(255) DEFAULT NULL,
  `signed_date` datetime DEFAULT NULL,
  `expiry_date` date DEFAULT NULL,
  `terms` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `maintenance_requests`
--

CREATE TABLE `maintenance_requests` (
  `request_id` int(11) NOT NULL,
  `property_id` int(11) NOT NULL,
  `room_id` int(11) DEFAULT NULL,
  `tenant_id` int(11) NOT NULL,
  `issue_type` enum('plumbing','electrical','cleaning','furniture','appliance','security','other') DEFAULT 'other',
  `description` text NOT NULL,
  `priority` enum('low','medium','high','urgent') DEFAULT 'medium',
  `status` enum('pending','in_progress','completed','cancelled') DEFAULT 'pending',
  `assigned_to` int(11) DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `messages`
--

CREATE TABLE `messages` (
  `message_id` int(11) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `content` text NOT NULL,
  `sent_at` datetime DEFAULT current_timestamp(),
  `is_read` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

CREATE TABLE `notifications` (
  `notification_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `type` enum('booking','payment','message','review','maintenance','system') NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `is_read` tinyint(1) DEFAULT 0,
  `related_id` int(11) DEFAULT NULL,
  `related_type` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `payment_id` int(11) NOT NULL,
  `booking_id` int(11) NOT NULL,
  `tenant_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `amount_paid` decimal(10,2) NOT NULL,
  `payment_date` datetime DEFAULT current_timestamp(),
  `payment_method` enum('cash','gcash','bank_transfer','online','paypal','other') NOT NULL,
  `status` enum('pending','confirmed','failed','refunded') DEFAULT 'pending'
) ;

--
-- Dumping data for table `payments`
--

INSERT INTO `payments` (`payment_id`, `booking_id`, `tenant_id`, `room_id`, `amount_paid`, `payment_date`, `payment_method`, `status`) VALUES
(1, 1, 5, 1, 4500.00, '2026-01-01 23:27:34', 'cash', 'confirmed'),
(2, 2, 9, 3, 3500.00, '2026-01-01 23:27:34', 'gcash', 'confirmed'),
(3, 3, 10, 3, 3500.00, '2026-01-01 23:27:34', 'gcash', 'confirmed'),
(4, 6, 13, 4, 5000.00, '2026-01-01 23:27:34', 'bank_transfer', 'confirmed'),
(5, 8, 15, 5, 7500.00, '2026-01-01 23:27:34', 'online', 'confirmed'),
(6, 10, 17, 8, 8500.00, '2026-01-01 23:27:34', 'cash', 'pending');

-- --------------------------------------------------------

--
-- Table structure for table `payment_receipts`
--

CREATE TABLE `payment_receipts` (
  `receipt_id` int(11) NOT NULL,
  `payment_id` int(11) NOT NULL,
  `receipt_number` varchar(50) NOT NULL,
  `receipt_url` varchar(255) DEFAULT NULL,
  `issued_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `payment_receipts`
--

INSERT INTO `payment_receipts` (`receipt_id`, `payment_id`, `receipt_number`, `receipt_url`, `issued_at`) VALUES
(1, 1, 'OR-001', NULL, '2026-01-01 23:27:34'),
(2, 2, 'OR-002', NULL, '2026-01-01 23:27:34'),
(3, 3, 'OR-003', NULL, '2026-01-01 23:27:34'),
(4, 4, 'OR-004', NULL, '2026-01-01 23:27:34'),
(5, 5, 'OR-005', NULL, '2026-01-01 23:27:34');

-- --------------------------------------------------------

--
-- Table structure for table `payment_schedules`
--

CREATE TABLE `payment_schedules` (
  `schedule_id` int(11) NOT NULL,
  `booking_id` int(11) NOT NULL,
  `due_date` date NOT NULL,
  `amount_due` decimal(10,2) NOT NULL,
  `status` enum('pending','paid','overdue','cancelled') DEFAULT 'pending',
  `paid_at` datetime DEFAULT NULL,
  `payment_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ;

--
-- Dumping data for table `payment_schedules`
--

INSERT INTO `payment_schedules` (`schedule_id`, `booking_id`, `due_date`, `amount_due`, `status`, `paid_at`, `payment_id`, `created_at`) VALUES
(1, 1, '2026-02-01', 4500.00, 'pending', NULL, NULL, '2026-01-01 23:27:34'),
(2, 2, '2026-02-05', 3500.00, 'pending', NULL, NULL, '2026-01-01 23:27:34'),
(3, 8, '2026-02-15', 7500.00, 'pending', NULL, NULL, '2026-01-01 23:27:34');

-- --------------------------------------------------------

--
-- Table structure for table `properties`
--

CREATE TABLE `properties` (
  `property_id` int(11) NOT NULL,
  `owner_id` int(11) NOT NULL,
  `property_name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `location` varchar(255) NOT NULL,
  `available_rooms` int(11) DEFAULT 0,
  `date_posted` datetime DEFAULT current_timestamp(),
  `status` enum('pending','approved','rejected') DEFAULT 'pending',
  `approved_by` int(11) DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `properties`
--

INSERT INTO `properties` (`property_id`, `owner_id`, `property_name`, `description`, `location`, `available_rooms`, `date_posted`, `status`, `approved_by`, `approved_at`, `deleted_at`) VALUES
(1, 2, 'Santos Boarding House', 'A quiet and secure boarding house near university belt. Ideal for students looking for a comfortable place to stay.', 'Manila, Metro Manila', 1, '2025-12-31 10:37:41', 'approved', NULL, NULL, NULL),
(2, 3, 'Dela Cruz Dormitory', 'Affordable dormitory with free Wi-Fi, laundry area, and 24/7 security. Perfect for college students.', 'Quezon City, Metro Manila', 0, '2025-12-31 10:37:41', 'approved', NULL, NULL, NULL),
(3, 7, 'Lim Residences', 'Walking distance to UST and FEU. Secure building with CCTV and bio-metric entry. Ideal for serious students.', 'Sampaloc, Manila', 2, '2026-01-01 23:25:29', 'approved', NULL, NULL, NULL),
(4, 8, 'Greenview Apartments', 'Modern studio apartments near Makati CBD. Includes gym access and rooftop garden. Perfect for young professionals.', 'Makati City, Metro Manila', 3, '2026-01-01 23:25:29', 'approved', NULL, NULL, NULL),
(5, 7, 'Glradiolyns', 'Right beside Pangasinan State University', 'Urdaneta City, Pangasinan', 1, '2026-01-02 18:17:43', 'approved', 1, '2026-01-02 18:18:14', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `property_amenities`
--

CREATE TABLE `property_amenities` (
  `amenity_id` int(11) NOT NULL,
  `property_id` int(11) NOT NULL,
  `amenity_name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `property_amenities`
--

INSERT INTO `property_amenities` (`amenity_id`, `property_id`, `amenity_name`) VALUES
(4, 1, '24/7 Security'),
(3, 1, 'Laundry Area'),
(2, 1, 'Parking'),
(1, 1, 'WiFi'),
(6, 2, 'Laundry Area'),
(7, 2, 'Study Area'),
(5, 2, 'WiFi'),
(10, 3, '24/7 Security'),
(11, 3, 'CCTV'),
(9, 3, 'Study Area'),
(8, 3, 'WiFi'),
(12, 4, 'Air Conditioning'),
(13, 4, 'Gym'),
(14, 4, 'Parking'),
(16, 4, 'Swimming Pool'),
(15, 4, 'WiFi'),
(18, 5, 'CCTV'),
(19, 5, 'Public Rooftop'),
(17, 5, 'WiFi');

-- --------------------------------------------------------

--
-- Table structure for table `property_images`
--

CREATE TABLE `property_images` (
  `image_id` int(11) NOT NULL,
  `property_id` int(11) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `is_primary` tinyint(1) DEFAULT 0,
  `uploaded_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reviews`
--

CREATE TABLE `reviews` (
  `review_id` int(11) NOT NULL,
  `tenant_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `rating` int(11) DEFAULT NULL CHECK (`rating` between 1 and 5),
  `comment` text DEFAULT NULL,
  `date_posted` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE `rooms` (
  `room_id` int(11) NOT NULL,
  `property_id` int(11) NOT NULL,
  `room_type` enum('Single','Shared') NOT NULL,
  `available_tenants` int(11) NOT NULL DEFAULT 1,
  `monthly_rate` decimal(10,2) NOT NULL,
  `description` text DEFAULT NULL,
  `total_tenants` int(11) NOT NULL DEFAULT 1,
  `current_tenants` int(11) DEFAULT 0,
  `house_rules` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `deleted_at` datetime DEFAULT NULL
) ;

--
-- Dumping data for table `rooms`
--

INSERT INTO `rooms` (`room_id`, `property_id`, `room_type`, `available_tenants`, `monthly_rate`, `description`, `total_tenants`, `current_tenants`, `house_rules`, `created_at`, `deleted_at`) VALUES
(1, 1, 'Single', 0, 4500.00, 'Cozy single room near the university, includes WiFi and shared kitchen access.', 1, 1, 'No smoking, No pets, Quiet hours: 10 PM - 6 AM', '2025-12-31 10:37:41', NULL),
(2, 1, 'Shared', 2, 4000.00, 'Shared room with 2 beds, good for budget-conscious students.', 2, 0, 'No smoking, No pets, Respect roommate privacy', '2025-12-31 10:37:41', NULL),
(3, 3, 'Shared', 1, 3500.00, 'Spacious quad-sharing room with individual lockers.', 4, 3, 'No visitors after 9PM, Clean as you go', '2026-01-01 23:25:29', NULL),
(4, 3, 'Shared', 1, 5000.00, 'Double deck bed for 2 pax, air-conditioned.', 2, 1, 'No smoking, Electric bill split by tenants', '2026-01-01 23:25:29', NULL),
(5, 3, 'Single', 0, 7500.00, 'Private solo room with own study table.', 1, 1, 'No pets allowed', '2026-01-01 23:25:29', NULL),
(6, 4, 'Single', 1, 15000.00, 'Premium studio unit with city view.', 1, 0, 'No loud parties, Pets allowed (small breeds only)', '2026-01-01 23:25:29', NULL),
(7, 4, 'Single', 1, 12000.00, 'Cozy single unit, inner facing (quiet).', 1, 0, 'No smoking inside the unit', '2026-01-01 23:25:29', NULL),
(8, 4, 'Shared', 1, 8500.00, 'Twin sharing deluxe room.', 2, 1, 'Keep noise to a minimum', '2026-01-01 23:25:29', NULL),
(9, 5, 'Single', 3, 2000.00, 'Rooms for 2nd and Third Floor', 4, 1, '', '2026-01-02 18:17:43', NULL);

--
-- Triggers `rooms`
--
DELIMITER $$
CREATE TRIGGER `update_property_available_rooms` AFTER UPDATE ON `rooms` FOR EACH ROW BEGIN
  IF NEW.available_tenants != OLD.available_tenants OR NEW.deleted_at IS NULL != OLD.deleted_at IS NULL THEN
    UPDATE properties p
    SET available_rooms = (
      SELECT COUNT(*) 
      FROM rooms r 
      WHERE r.property_id = p.property_id 
        AND r.deleted_at IS NULL 
        AND r.available_tenants > 0
    )
    WHERE p.property_id = NEW.property_id;
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `room_availability`
--

CREATE TABLE `room_availability` (
  `availability_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `date` date NOT NULL,
  `is_available` tinyint(1) DEFAULT 1,
  `reason` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `room_images`
--

CREATE TABLE `room_images` (
  `image_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `is_primary` tinyint(1) DEFAULT 0,
  `uploaded_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `full_name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `role` enum('tenant','owner','admin') NOT NULL DEFAULT 'tenant',
  `status` enum('pending','approved','rejected') DEFAULT 'pending',
  `role_change_request` enum('tenant','owner') DEFAULT NULL,
  `approved_by` int(11) DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `date_registered` datetime DEFAULT current_timestamp(),
  `deleted_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `full_name`, `email`, `password`, `phone_number`, `role`, `status`, `role_change_request`, `approved_by`, `approved_at`, `date_registered`, `deleted_at`) VALUES
(1, 'Admin User', 'admin@rentease.com', 'admin123', '09170000000', 'admin', 'approved', NULL, NULL, '2026-01-02 16:26:04', '2025-12-31 10:37:41', NULL),
(2, 'Maria Santos', 'maria.santos@rentease.com', 'owner123', '09171234567', 'owner', 'approved', NULL, NULL, '2025-12-31 10:37:41', '2025-12-31 10:37:41', NULL),
(3, 'John Dela Cruz', 'john.delacruz@rentease.com', 'owner123', '09179876543', 'owner', 'approved', NULL, NULL, '2025-12-31 10:37:41', '2025-12-31 10:37:41', NULL),
(4, 'Angela Reyes', 'angela.reyes@rentease.com', 'owner123', '09173451234', 'owner', 'approved', NULL, NULL, '2025-12-31 10:37:41', '2025-12-31 10:37:41', NULL),
(5, 'Kevin Mendoza', 'kevin.mendoza@student.com', 'tenant123', '09181234567', 'tenant', 'approved', NULL, NULL, '2025-12-31 10:37:41', '2025-12-31 10:37:41', NULL),
(6, 'Jessica Tan', 'jessica.tan@student.com', 'tenant123', '09182345678', 'tenant', 'approved', NULL, NULL, '2025-12-31 10:37:41', '2025-12-31 10:37:41', NULL),
(7, 'Robert Lim', 'robert.lim@rentease.com', 'owner123', '09175551001', 'owner', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(8, 'Elena Go', 'elena.go@rentease.com', 'owner123', '09175551002', 'owner', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(9, 'Mark Dizon', 'mark.dizon@student.com', 'tenant123', '09185552001', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(10, 'Sarah Lee', 'sarah.lee@student.com', 'tenant123', '09185552002', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(11, 'Miguel Castro', 'miguel.castro@student.com', 'tenant123', '09185552003', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(12, 'Patricia Vega', 'patricia.vega@student.com', 'tenant123', '09185552004', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:25:29', '2026-01-01 23:25:29', NULL),
(13, 'Gabriel Ramos', 'gabriel.ramos@student.com', 'tenant123', '09191000001', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(14, 'Sofia Mendoza', 'sofia.mendoza@student.com', 'tenant123', '09191000002', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(15, 'Daniel Corpuz', 'daniel.corpuz@student.com', 'tenant123', '09191000003', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(16, 'Bea Tolentino', 'bea.tolentino@student.com', 'tenant123', '09191000004', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(17, 'Rafael Navarro', 'rafael.navarro@student.com', 'tenant123', '09191000005', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(18, 'Camille Aquino', 'camille.aquino@student.com', 'tenant123', '09191000006', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(19, 'Joshua Ferrer', 'joshua.ferrer@student.com', 'tenant123', '09191000007', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(20, 'Lara Bautista', 'lara.bautista@student.com', 'tenant123', '09191000008', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(21, 'Christian Roque', 'christian.roque@student.com', 'tenant123', '09191000009', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(22, 'Denise Salvador', 'denise.salvador@student.com', 'tenant123', '09191000010', 'tenant', 'approved', NULL, NULL, '2026-01-01 23:26:50', '2026-01-01 23:26:50', NULL),
(23, 'Tuvween Dela Torre', 'tuv@rentease.com', 'tenant123', NULL, 'owner', 'approved', NULL, 1, '2026-01-02 16:40:44', '2026-01-02 16:40:05', NULL),
(24, 'Tawade Dela Torre', 'taw@owner.com', 'owner123', NULL, 'owner', 'approved', NULL, 1, '2026-01-02 16:44:02', '2026-01-02 16:43:12', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `user_profiles`
--

CREATE TABLE `user_profiles` (
  `profile_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `date_of_birth` date DEFAULT NULL,
  `address` text DEFAULT NULL,
  `emergency_contact_name` varchar(100) DEFAULT NULL,
  `emergency_contact_phone` varchar(20) DEFAULT NULL,
  `profile_image_url` varchar(255) DEFAULT NULL,
  `bio` text DEFAULT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_active_bookings`
-- (See below for the actual view)
--
CREATE TABLE `vw_active_bookings` (
`booking_id` int(11)
,`tenant_id` int(11)
,`tenant_name` varchar(100)
,`tenant_email` varchar(100)
,`room_id` int(11)
,`room_type` enum('Single','Shared')
,`monthly_rate` decimal(10,2)
,`property_id` int(11)
,`property_name` varchar(100)
,`location` varchar(255)
,`start_date` date
,`end_date` date
,`status` enum('pending','approved','rejected','cancelled','completed')
,`created_at` datetime
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_property_stats`
-- (See below for the actual view)
--
CREATE TABLE `vw_property_stats` (
`property_id` int(11)
,`property_name` varchar(100)
,`owner_id` int(11)
,`owner_name` varchar(100)
,`total_rooms` bigint(21)
,`available_rooms` bigint(21)
,`total_bookings` bigint(21)
,`active_bookings` bigint(21)
,`avg_rating` decimal(14,4)
,`total_reviews` bigint(21)
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_tenant_dashboard`
-- (See below for the actual view)
--
CREATE TABLE `vw_tenant_dashboard` (
`tenant_id` int(11)
,`full_name` varchar(100)
,`email` varchar(100)
,`total_bookings` bigint(21)
,`active_bookings` bigint(21)
,`pending_bookings` bigint(21)
,`total_payments` bigint(21)
,`total_paid` decimal(32,2)
,`pending_payments` bigint(21)
,`total_due` decimal(32,2)
);

-- --------------------------------------------------------

--
-- Structure for view `vw_active_bookings`
--
DROP TABLE IF EXISTS `vw_active_bookings`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_active_bookings`  AS SELECT `b`.`booking_id` AS `booking_id`, `b`.`tenant_id` AS `tenant_id`, `u`.`full_name` AS `tenant_name`, `u`.`email` AS `tenant_email`, `b`.`room_id` AS `room_id`, `r`.`room_type` AS `room_type`, `r`.`monthly_rate` AS `monthly_rate`, `p`.`property_id` AS `property_id`, `p`.`property_name` AS `property_name`, `p`.`location` AS `location`, `b`.`start_date` AS `start_date`, `b`.`end_date` AS `end_date`, `b`.`status` AS `status`, `b`.`created_at` AS `created_at` FROM (((`bookings` `b` join `users` `u` on(`b`.`tenant_id` = `u`.`user_id`)) join `rooms` `r` on(`b`.`room_id` = `r`.`room_id`)) join `properties` `p` on(`r`.`property_id` = `p`.`property_id`)) WHERE `b`.`deleted_at` is null AND `b`.`status` in ('pending','approved') ;

-- --------------------------------------------------------

--
-- Structure for view `vw_property_stats`
--
DROP TABLE IF EXISTS `vw_property_stats`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_property_stats`  AS SELECT `p`.`property_id` AS `property_id`, `p`.`property_name` AS `property_name`, `p`.`owner_id` AS `owner_id`, `u`.`full_name` AS `owner_name`, count(distinct `r`.`room_id`) AS `total_rooms`, count(distinct case when `r`.`available_tenants` > 0 then `r`.`room_id` end) AS `available_rooms`, count(distinct `b`.`booking_id`) AS `total_bookings`, count(distinct case when `b`.`status` = 'approved' then `b`.`booking_id` end) AS `active_bookings`, avg(`rev`.`rating`) AS `avg_rating`, count(distinct `rev`.`review_id`) AS `total_reviews` FROM ((((`properties` `p` join `users` `u` on(`p`.`owner_id` = `u`.`user_id`)) left join `rooms` `r` on(`p`.`property_id` = `r`.`property_id` and `r`.`deleted_at` is null)) left join `bookings` `b` on(`r`.`room_id` = `b`.`room_id` and `b`.`deleted_at` is null)) left join `reviews` `rev` on(`r`.`room_id` = `rev`.`room_id`)) WHERE `p`.`deleted_at` is null GROUP BY `p`.`property_id`, `p`.`property_name`, `p`.`owner_id`, `u`.`full_name` ;

-- --------------------------------------------------------

--
-- Structure for view `vw_tenant_dashboard`
--
DROP TABLE IF EXISTS `vw_tenant_dashboard`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_tenant_dashboard`  AS SELECT `u`.`user_id` AS `tenant_id`, `u`.`full_name` AS `full_name`, `u`.`email` AS `email`, count(distinct `b`.`booking_id`) AS `total_bookings`, count(distinct case when `b`.`status` = 'approved' then `b`.`booking_id` end) AS `active_bookings`, count(distinct case when `b`.`status` = 'pending' then `b`.`booking_id` end) AS `pending_bookings`, count(distinct `p`.`payment_id`) AS `total_payments`, sum(case when `p`.`status` = 'confirmed' then `p`.`amount_paid` else 0 end) AS `total_paid`, count(distinct `ps`.`schedule_id`) AS `pending_payments`, sum(case when `ps`.`status` = 'pending' then `ps`.`amount_due` else 0 end) AS `total_due` FROM (((`users` `u` left join `bookings` `b` on(`u`.`user_id` = `b`.`tenant_id` and `b`.`deleted_at` is null)) left join `payments` `p` on(`u`.`user_id` = `p`.`tenant_id`)) left join `payment_schedules` `ps` on(`b`.`booking_id` = `ps`.`booking_id`)) WHERE `u`.`role` = 'tenant' AND `u`.`deleted_at` is null GROUP BY `u`.`user_id`, `u`.`full_name`, `u`.`email` ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `analytics_events`
--
ALTER TABLE `analytics_events`
  ADD PRIMARY KEY (`event_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `booking_id` (`booking_id`),
  ADD KEY `idx_analytics_user` (`user_id`),
  ADD KEY `idx_analytics_type` (`event_type`),
  ADD KEY `idx_analytics_property` (`property_id`),
  ADD KEY `idx_analytics_date` (`created_at`),
  ADD KEY `idx_analytics_type_date` (`event_type`,`created_at`);

--
-- Indexes for table `audit_logs`
--
ALTER TABLE `audit_logs`
  ADD PRIMARY KEY (`log_id`),
  ADD KEY `idx_audit_user` (`user_id`),
  ADD KEY `idx_audit_table` (`table_name`),
  ADD KEY `idx_audit_action` (`action`),
  ADD KEY `idx_audit_date` (`created_at`);

--
-- Indexes for table `bookings`
--
ALTER TABLE `bookings`
  ADD PRIMARY KEY (`booking_id`),
  ADD KEY `idx_bookings_tenant` (`tenant_id`),
  ADD KEY `idx_bookings_room` (`room_id`),
  ADD KEY `idx_bookings_status` (`status`),
  ADD KEY `idx_bookings_dates` (`start_date`,`end_date`),
  ADD KEY `idx_bookings_deleted` (`deleted_at`);

--
-- Indexes for table `booking_history`
--
ALTER TABLE `booking_history`
  ADD PRIMARY KEY (`history_id`),
  ADD KEY `idx_booking_history_booking` (`booking_id`),
  ADD KEY `idx_booking_history_changed_by` (`changed_by`),
  ADD KEY `idx_booking_history_date` (`changed_at`);

--
-- Indexes for table `lease_agreements`
--
ALTER TABLE `lease_agreements`
  ADD PRIMARY KEY (`agreement_id`),
  ADD UNIQUE KEY `booking_id` (`booking_id`),
  ADD KEY `idx_lease_booking` (`booking_id`),
  ADD KEY `idx_lease_expiry` (`expiry_date`);

--
-- Indexes for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  ADD PRIMARY KEY (`request_id`),
  ADD KEY `idx_maintenance_property` (`property_id`),
  ADD KEY `idx_maintenance_room` (`room_id`),
  ADD KEY `idx_maintenance_tenant` (`tenant_id`),
  ADD KEY `idx_maintenance_status` (`status`),
  ADD KEY `idx_maintenance_priority` (`priority`),
  ADD KEY `idx_maintenance_assigned` (`assigned_to`);

--
-- Indexes for table `messages`
--
ALTER TABLE `messages`
  ADD PRIMARY KEY (`message_id`),
  ADD KEY `idx_messages_sender` (`sender_id`),
  ADD KEY `idx_messages_receiver` (`receiver_id`),
  ADD KEY `idx_messages_users` (`sender_id`,`receiver_id`),
  ADD KEY `idx_messages_unread` (`receiver_id`,`is_read`),
  ADD KEY `idx_messages_date` (`sent_at`);

--
-- Indexes for table `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`notification_id`),
  ADD KEY `idx_notifications_user` (`user_id`),
  ADD KEY `idx_notifications_unread` (`user_id`,`is_read`),
  ADD KEY `idx_notifications_type` (`type`),
  ADD KEY `idx_notifications_date` (`created_at`);

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`payment_id`),
  ADD KEY `idx_payments_booking` (`booking_id`),
  ADD KEY `idx_payments_tenant` (`tenant_id`),
  ADD KEY `idx_payments_room` (`room_id`),
  ADD KEY `idx_payments_status` (`status`),
  ADD KEY `idx_payments_date` (`payment_date`);

--
-- Indexes for table `payment_receipts`
--
ALTER TABLE `payment_receipts`
  ADD PRIMARY KEY (`receipt_id`),
  ADD UNIQUE KEY `receipt_number` (`receipt_number`),
  ADD KEY `idx_receipts_payment` (`payment_id`),
  ADD KEY `idx_receipts_number` (`receipt_number`);

--
-- Indexes for table `payment_schedules`
--
ALTER TABLE `payment_schedules`
  ADD PRIMARY KEY (`schedule_id`),
  ADD KEY `idx_schedules_booking` (`booking_id`),
  ADD KEY `idx_schedules_due_date` (`due_date`),
  ADD KEY `idx_schedules_status` (`status`),
  ADD KEY `idx_schedules_payment` (`payment_id`);

--
-- Indexes for table `properties`
--
ALTER TABLE `properties`
  ADD PRIMARY KEY (`property_id`),
  ADD KEY `idx_properties_owner` (`owner_id`),
  ADD KEY `idx_properties_location` (`location`),
  ADD KEY `idx_properties_deleted` (`deleted_at`),
  ADD KEY `idx_properties_status` (`status`),
  ADD KEY `properties_approved_by_fk` (`approved_by`);

--
-- Indexes for table `property_amenities`
--
ALTER TABLE `property_amenities`
  ADD PRIMARY KEY (`amenity_id`),
  ADD UNIQUE KEY `unique_property_amenity` (`property_id`,`amenity_name`),
  ADD KEY `idx_amenities_property` (`property_id`);

--
-- Indexes for table `property_images`
--
ALTER TABLE `property_images`
  ADD PRIMARY KEY (`image_id`),
  ADD KEY `idx_prop_images_property` (`property_id`),
  ADD KEY `idx_prop_images_primary` (`property_id`,`is_primary`);

--
-- Indexes for table `reviews`
--
ALTER TABLE `reviews`
  ADD PRIMARY KEY (`review_id`),
  ADD UNIQUE KEY `unique_tenant_room_review` (`tenant_id`,`room_id`),
  ADD KEY `idx_reviews_tenant` (`tenant_id`),
  ADD KEY `idx_reviews_room` (`room_id`),
  ADD KEY `idx_reviews_rating` (`rating`),
  ADD KEY `idx_reviews_date` (`date_posted`);

--
-- Indexes for table `rooms`
--
ALTER TABLE `rooms`
  ADD PRIMARY KEY (`room_id`),
  ADD KEY `idx_rooms_property` (`property_id`),
  ADD KEY `idx_rooms_type` (`room_type`),
  ADD KEY `idx_rooms_deleted` (`deleted_at`);

--
-- Indexes for table `room_availability`
--
ALTER TABLE `room_availability`
  ADD PRIMARY KEY (`availability_id`),
  ADD UNIQUE KEY `unique_room_date` (`room_id`,`date`),
  ADD KEY `idx_availability_room` (`room_id`),
  ADD KEY `idx_availability_date` (`date`),
  ADD KEY `idx_availability_status` (`room_id`,`is_available`,`date`);

--
-- Indexes for table `room_images`
--
ALTER TABLE `room_images`
  ADD PRIMARY KEY (`image_id`),
  ADD KEY `idx_room_images_room` (`room_id`),
  ADD KEY `idx_room_images_primary` (`room_id`,`is_primary`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `idx_users_email` (`email`),
  ADD KEY `idx_users_role` (`role`),
  ADD KEY `idx_users_deleted` (`deleted_at`),
  ADD KEY `idx_users_status` (`status`),
  ADD KEY `users_approved_by_fk` (`approved_by`);

--
-- Indexes for table `user_profiles`
--
ALTER TABLE `user_profiles`
  ADD PRIMARY KEY (`profile_id`),
  ADD UNIQUE KEY `user_id` (`user_id`),
  ADD KEY `idx_profiles_user` (`user_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `analytics_events`
--
ALTER TABLE `analytics_events`
  MODIFY `event_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `audit_logs`
--
ALTER TABLE `audit_logs`
  MODIFY `log_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `bookings`
--
ALTER TABLE `bookings`
  MODIFY `booking_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `booking_history`
--
ALTER TABLE `booking_history`
  MODIFY `history_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `lease_agreements`
--
ALTER TABLE `lease_agreements`
  MODIFY `agreement_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  MODIFY `request_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `messages`
--
ALTER TABLE `messages`
  MODIFY `message_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `notification_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `payment_receipts`
--
ALTER TABLE `payment_receipts`
  MODIFY `receipt_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `payment_schedules`
--
ALTER TABLE `payment_schedules`
  MODIFY `schedule_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `properties`
--
ALTER TABLE `properties`
  MODIFY `property_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `property_amenities`
--
ALTER TABLE `property_amenities`
  MODIFY `amenity_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- AUTO_INCREMENT for table `property_images`
--
ALTER TABLE `property_images`
  MODIFY `image_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reviews`
--
ALTER TABLE `reviews`
  MODIFY `review_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rooms`
--
ALTER TABLE `rooms`
  MODIFY `room_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `room_availability`
--
ALTER TABLE `room_availability`
  MODIFY `availability_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `room_images`
--
ALTER TABLE `room_images`
  MODIFY `image_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT for table `user_profiles`
--
ALTER TABLE `user_profiles`
  MODIFY `profile_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `analytics_events`
--
ALTER TABLE `analytics_events`
  ADD CONSTRAINT `analytics_events_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  ADD CONSTRAINT `analytics_events_ibfk_2` FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`) ON DELETE SET NULL,
  ADD CONSTRAINT `analytics_events_ibfk_3` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE SET NULL,
  ADD CONSTRAINT `analytics_events_ibfk_4` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`) ON DELETE SET NULL;

--
-- Constraints for table `audit_logs`
--
ALTER TABLE `audit_logs`
  ADD CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `bookings`
--
ALTER TABLE `bookings`
  ADD CONSTRAINT `bookings_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `bookings_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `booking_history`
--
ALTER TABLE `booking_history`
  ADD CONSTRAINT `booking_history_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `booking_history_ibfk_2` FOREIGN KEY (`changed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `lease_agreements`
--
ALTER TABLE `lease_agreements`
  ADD CONSTRAINT `lease_agreements_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`) ON DELETE CASCADE;

--
-- Constraints for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  ADD CONSTRAINT `maintenance_requests_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `maintenance_requests_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE SET NULL,
  ADD CONSTRAINT `maintenance_requests_ibfk_3` FOREIGN KEY (`tenant_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `maintenance_requests_ibfk_4` FOREIGN KEY (`assigned_to`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `messages`
--
ALTER TABLE `messages`
  ADD CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payments_ibfk_2` FOREIGN KEY (`tenant_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payments_ibfk_3` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `payment_receipts`
--
ALTER TABLE `payment_receipts`
  ADD CONSTRAINT `payment_receipts_ibfk_1` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`payment_id`) ON DELETE CASCADE;

--
-- Constraints for table `payment_schedules`
--
ALTER TABLE `payment_schedules`
  ADD CONSTRAINT `payment_schedules_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payment_schedules_ibfk_2` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`payment_id`) ON DELETE SET NULL;

--
-- Constraints for table `properties`
--
ALTER TABLE `properties`
  ADD CONSTRAINT `properties_approved_by_fk` FOREIGN KEY (`approved_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  ADD CONSTRAINT `properties_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `property_amenities`
--
ALTER TABLE `property_amenities`
  ADD CONSTRAINT `property_amenities_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`) ON DELETE CASCADE;

--
-- Constraints for table `property_images`
--
ALTER TABLE `property_images`
  ADD CONSTRAINT `property_images_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`) ON DELETE CASCADE;

--
-- Constraints for table `reviews`
--
ALTER TABLE `reviews`
  ADD CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `rooms`
--
ALTER TABLE `rooms`
  ADD CONSTRAINT `rooms_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`) ON DELETE CASCADE;

--
-- Constraints for table `room_availability`
--
ALTER TABLE `room_availability`
  ADD CONSTRAINT `room_availability_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `room_images`
--
ALTER TABLE `room_images`
  ADD CONSTRAINT `room_images_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `users_approved_by_fk` FOREIGN KEY (`approved_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `user_profiles`
--
ALTER TABLE `user_profiles`
  ADD CONSTRAINT `user_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
