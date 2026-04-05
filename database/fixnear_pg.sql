-- ============================================
-- FixNear Database Schema (PostgreSQL version)
-- For Neon.tech / Render deployment
-- ============================================

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    address TEXT DEFAULT NULL,
    city VARCHAR(100) DEFAULT '',
    profile_image VARCHAR(255) DEFAULT NULL,
    reset_token VARCHAR(100) DEFAULT NULL,
    reset_token_expiry TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SERVICES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TECHNICIANS TABLE (linked to users)
-- ============================================
CREATE TABLE IF NOT EXISTS technicians (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(150),
    service_id INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    experience_years INT DEFAULT 0,
    rating DECIMAL(2,1) DEFAULT 0.0,
    total_jobs INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- BOOKINGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_id INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    technician_id INT DEFAULT NULL REFERENCES technicians(id) ON DELETE SET NULL,
    booking_date DATE NOT NULL,
    time_slot VARCHAR(30) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) DEFAULT '',
    phone VARCHAR(20) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    total_price DECIMAL(10,2) DEFAULT 0.00,
    notes TEXT,
    attachment VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- REVIEWS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booking_id INT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CONTACT MESSAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS contact_messages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    subject VARCHAR(200) DEFAULT '',
    message TEXT NOT NULL,
    is_read SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
-- SEED DATA: Admin user (password will be re-hashed by setup script)
-- Temporary placeholder hash — run setup_db_pg.py to set correct passwords
-- ============================================
INSERT INTO users (name, email, phone, password, role) VALUES
('Admin', 'admin@fixnear.com', '9999999999', 'TEMP_HASH_RUN_SETUP', 'admin');

-- ============================================
-- SEED DATA: Technician users
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
