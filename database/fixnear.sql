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
-- SEED DATA: Services
-- ============================================
INSERT INTO services (name, icon, description, price) VALUES
('Electrician', 'fa-bolt', 'Wiring, switches, repairs & installations', 299.00),
('Plumber', 'fa-wrench', 'Pipe fixing, leakage repair & fittings', 249.00),
('AC Repair', 'fa-snowflake', 'AC servicing, gas refill & installation', 499.00),
('Carpenter', 'fa-hammer', 'Furniture repair, door fixing & woodwork', 349.00),
('Painter', 'fa-paint-roller', 'Wall painting, waterproofing & design', 599.00);

-- ============================================
-- SEED DATA: Admin user (password: admin123)
-- ============================================
INSERT INTO users (name, email, phone, password, role) VALUES
('Admin', 'admin@fixnear.com', '9999999999', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin');

-- ============================================
-- SEED DATA: Technician users (password: tech123)
-- ============================================
INSERT INTO users (name, email, phone, password, role) VALUES
('Rajesh Kumar', 'rajesh@fixnear.com', '9876543210', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Amit Sharma', 'amit@fixnear.com', '9876543211', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Sunil Verma', 'sunil@fixnear.com', '9876543212', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Vikram Singh', 'vikram@fixnear.com', '9876543213', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Rakesh Yadav', 'rakesh@fixnear.com', '9876543214', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Deepak Joshi', 'deepak@fixnear.com', '9876543215', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Manoj Tiwari', 'manoj@fixnear.com', '9876543216', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Arun Gupta', 'arun@fixnear.com', '9876543217', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Sanjay Patel', 'sanjay@fixnear.com', '9876543218', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician'),
('Kiran Das', 'kiran@fixnear.com', '9876543219', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'technician');

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
