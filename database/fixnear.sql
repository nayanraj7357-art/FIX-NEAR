-- ============================================
-- FixNear Database Schema
-- ============================================

DROP DATABASE IF EXISTS fixnear;
CREATE DATABASE fixnear CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE fixnear;

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin', 'technician') DEFAULT 'user',
    address TEXT DEFAULT NULL,
    city VARCHAR(100) DEFAULT '',
    profile_image VARCHAR(255) DEFAULT NULL,
    reset_token VARCHAR(100) DEFAULT NULL,
    reset_token_expiry DATETIME DEFAULT NULL,
    last_login_at DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- SERVICES TABLE
-- ============================================
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) DEFAULT 0.00,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- TECHNICIANS TABLE (linked to users)
-- ============================================
CREATE TABLE technicians (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(150),
    service_id INT NOT NULL,
    experience_years INT DEFAULT 0,
    rating DECIMAL(2,1) DEFAULT 0.0,
    total_jobs INT DEFAULT 0,
    status ENUM('available', 'busy', 'offline') DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- BOOKINGS TABLE
-- ============================================
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    service_id INT NOT NULL,
    technician_id INT DEFAULT NULL,
    booking_date DATE NOT NULL,
    time_slot VARCHAR(30) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) DEFAULT '',
    phone VARCHAR(20) NOT NULL,
    status ENUM('pending', 'confirmed', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    total_price DECIMAL(10,2) DEFAULT 0.00,
    notes TEXT,
    attachment VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================
-- REVIEWS TABLE
-- ============================================
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    booking_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- CONTACT MESSAGES TABLE
-- ============================================
CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    subject VARCHAR(200) DEFAULT '',
    message TEXT NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(40) DEFAULT 'general',
    related_booking_id INT DEFAULT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_booking_id) REFERENCES bookings(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================
-- NOTIFICATION PREFERENCES TABLE
-- ============================================
CREATE TABLE notification_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    booking_updates TINYINT(1) DEFAULT 1,
    assignment_updates TINYINT(1) DEFAULT 1,
    system_updates TINYINT(1) DEFAULT 1,
    email_notifications TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- SEED DATA: Services
-- ============================================
INSERT INTO services (name, icon, description, price) VALUES
('Electrician', 'fa-bolt', 'Wiring, switches, repairs & installations', 299.00),
('Plumber', 'fa-wrench', 'Pipe fixing, leakage repair & fittings', 249.00),
('AC Repair', 'fa-snowflake', 'AC servicing, gas refill & installation', 499.00),
('Carpenter', 'fa-hammer', 'Furniture repair, door fixing & woodwork', 349.00),
('Painter', 'fa-paint-roller', 'Wall painting, waterproofing & design', 599.00);

-- ============================================
-- SEED DATA: Admin user (password will be set by setup_db.py)
-- Temporary placeholder — run setup_db.py to set secure passwords
-- ============================================
INSERT INTO users (name, email, phone, password, role) VALUES
('Admin', 'admin@fixnear.com', '9999999999', 'TEMP_HASH_RUN_SETUP', 'admin');

-- ============================================
-- SEED DATA: Technician users (passwords will be set by setup_db.py)
-- ============================================
INSERT INTO users (name, email, phone, password, role) VALUES
('Rajesh Kumar', 'rajesh@fixnear.com', '9876543210', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Amit Sharma', 'amit@fixnear.com', '9876543211', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Sunil Verma', 'sunil@fixnear.com', '9876543212', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Vikram Singh', 'vikram@fixnear.com', '9876543213', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Rakesh Yadav', 'rakesh@fixnear.com', '9876543214', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Deepak Joshi', 'deepak@fixnear.com', '9876543215', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Manoj Tiwari', 'manoj@fixnear.com', '9876543216', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Arun Gupta', 'arun@fixnear.com', '9876543217', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Sanjay Patel', 'sanjay@fixnear.com', '9876543218', 'TEMP_HASH_RUN_SETUP', 'technician'),
('Kiran Das', 'kiran@fixnear.com', '9876543219', 'TEMP_HASH_RUN_SETUP', 'technician');

-- ============================================
-- SEED DATA: Technician profiles (linked to user accounts)
-- ============================================
INSERT INTO technicians (user_id, name, phone, email, service_id, experience_years, rating) VALUES
(2, 'Rajesh Kumar', '9876543210', 'rajesh@fixnear.com', 1, 8, 4.8),
(3, 'Amit Sharma', '9876543211', 'amit@fixnear.com', 1, 5, 4.5),
(4, 'Sunil Verma', '9876543212', 'sunil@fixnear.com', 2, 10, 4.9),
(5, 'Vikram Singh', '9876543213', 'vikram@fixnear.com', 2, 6, 4.6),
(6, 'Rakesh Yadav', '9876543214', 'rakesh@fixnear.com', 3, 7, 4.7),
(7, 'Deepak Joshi', '9876543215', 'deepak@fixnear.com', 3, 4, 4.3),
(8, 'Manoj Tiwari', '9876543216', 'manoj@fixnear.com', 4, 12, 4.9),
(9, 'Arun Gupta', '9876543217', 'arun@fixnear.com', 4, 3, 4.2),
(10, 'Sanjay Patel', '9876543218', 'sanjay@fixnear.com', 5, 9, 4.8),
(11, 'Kiran Das', '9876543219', 'kiran@fixnear.com', 5, 5, 4.4);

-- ============================================
-- SEED DATA: Notification preferences for all seed users
-- ============================================
INSERT INTO notification_preferences (user_id)
SELECT id FROM users;
