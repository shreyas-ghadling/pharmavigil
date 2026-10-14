-- =====================================================================
-- PHARMAVIGIL: RELATIONAL DATABASE DDL SCHEMA (MySQL 8.0+)
-- ACID-Compliant Pharmaceutical Supply Chain and Traceability Schema
-- =====================================================================

CREATE DATABASE IF NOT EXISTS pharmavigil_db;
USE pharmavigil_db;

-- Drop tables in reverse foreign key order for clean recreation
DROP TABLE IF EXISTS recall_audit;
DROP TABLE IF EXISTS batch_distribution;
DROP TABLE IF EXISTS stock_receipts;
DROP TABLE IF EXISTS app_schema_migrations;
DROP TABLE IF EXISTS batches;
DROP TABLE IF EXISTS medicines;
DROP TABLE IF EXISTS manufacturers;
DROP TABLE IF EXISTS hospitals;
DROP TABLE IF EXISTS users;

-- 1. MANUFACTURERS TABLE
CREATE TABLE manufacturers (
    manufacturer_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    license_number VARCHAR(50) NOT NULL UNIQUE,
    country VARCHAR(60) NOT NULL,
    contact_email VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. MEDICINES TABLE
CREATE TABLE medicines (
    medicine_id INT AUTO_INCREMENT PRIMARY KEY,
    commercial_name VARCHAR(150) NOT NULL,
    generic_name VARCHAR(150) NOT NULL,
    dosage_form VARCHAR(50) NOT NULL,
    strength VARCHAR(50) NOT NULL,
    manufacturer_id INT NOT NULL,
    CONSTRAINT fk_medicine_manufacturer 
        FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(manufacturer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. BATCHES TABLE
CREATE TABLE batches (
    batch_number VARCHAR(50) PRIMARY KEY,
    medicine_id INT NOT NULL,
    manufacturing_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    total_units_produced INT NOT NULL,
    recall_status VARCHAR(25) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT fk_batch_medicine 
        FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_total_units_produced 
        CHECK (total_units_produced > 0),
    CONSTRAINT chk_batch_expiry_dates 
        CHECK (expiry_date > manufacturing_date),
    CONSTRAINT chk_batch_recall_status 
        CHECK (recall_status IN ('ACTIVE', 'UNDER_INVESTIGATION', 'RECALLED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. HOSPITALS TABLE
CREATE TABLE app_schema_migrations (name VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE stock_receipts (
    receipt_id INT AUTO_INCREMENT PRIMARY KEY,
    batch_number VARCHAR(50) NOT NULL,
    quantity_received INT NOT NULL,
    receipt_date DATE NOT NULL,
    reference VARCHAR(100) NOT NULL,
    source_type VARCHAR(25) NOT NULL DEFAULT 'RECEIPT',
    recorded_by VARCHAR(100) NOT NULL,
    CONSTRAINT fk_receipt_batch FOREIGN KEY (batch_number) REFERENCES batches(batch_number),
    CONSTRAINT chk_receipt_quantity CHECK (quantity_received > 0),
    UNIQUE KEY uq_receipt_reference (batch_number, reference)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE hospitals (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. BATCH_DISTRIBUTION TABLE
CREATE TABLE batch_distribution (
    distribution_id INT AUTO_INCREMENT PRIMARY KEY,
    batch_number VARCHAR(50) NOT NULL,
    hospital_id INT NOT NULL,
    quantity_delivered INT NOT NULL,
    dispatch_date DATE NOT NULL,
    CONSTRAINT fk_dist_batch 
        FOREIGN KEY (batch_number) REFERENCES batches(batch_number)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_dist_hospital 
        FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_quantity_delivered 
        CHECK (quantity_delivered > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. USERS TABLE (Bcrypt Authentication & RBAC)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_user_role 
        CHECK (role IN ('DOCTOR_PATIENT', 'PHARMACIST', 'SAFETY_OFFICER_ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. RECALL_AUDIT TABLE
CREATE TABLE recall_audit (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    batch_number VARCHAR(50) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    recalled_by VARCHAR(100) NOT NULL DEFAULT 'SAFETY_OFFICER_ADMIN',
    affected_hospitals INT NOT NULL DEFAULT 0,
    total_units_recalled INT NOT NULL DEFAULT 0,
    recalled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_batch 
        FOREIGN KEY (batch_number) REFERENCES batches(batch_number)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
