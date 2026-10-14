-- =====================================================================
-- PHARMAVIGIL: SEED DATA (MySQL 8.0+)
-- Realistic Data for Presentation, Query Execution & Supply Chain Tracking
-- Uses dates relative to CURDATE() so demo state is always current:
-- 1 Expired Batch, 2 Expiring within 30 days, 7 Active Batches
-- =====================================================================

USE pharmavigil_db;

-- 0. EMPTY RECALL AUDIT LOG (Fresh demo starts with 0 audit entries)
DELETE FROM recall_audit;
ALTER TABLE recall_audit AUTO_INCREMENT = 1;

-- 1. SEED MANUFACTURERS (3 Manufacturers)
INSERT INTO manufacturers (manufacturer_id, company_name, license_number, country, contact_email) VALUES
(1, 'Apex Pharma Global', 'LIC-APX-9901', 'Germany', 'compliance@apexpharma.de'),
(2, 'NovaCare Therapeutics', 'LIC-NOV-4421', 'United States', 'safety@novacare.com'),
(3, 'Zenith BioLabs', 'LIC-ZNT-8812', 'India', 'regulatory@zenithbiolabs.in')
ON DUPLICATE KEY UPDATE company_name=VALUES(company_name);

-- 2. SEED MEDICINES (6 Medicines)
INSERT INTO medicines (medicine_id, commercial_name, generic_name, dosage_form, strength, manufacturer_id) VALUES
(101, 'Cardiomax', 'Amlodipine Besylate', 'Tablet', '5 mg', 1),
(102, 'Neurocalm', 'Pregabalin', 'Capsule', '75mg', 2),
(103, 'Glucoguard', 'Metformin HCl', 'Tablet', '500mg', 3),
(104, 'PulmoBreeze', 'Salbutamol Sulfate', 'Inhalation Spray', '100 mcg/actuation', 1),
(105, 'GastroRelief', 'Omeprazole', 'Capsule', '20mg', 2),
(106, 'Dermacure', 'Hydrocortisone', 'Cream', '10 mg/g (1%)', 3)
ON DUPLICATE KEY UPDATE commercial_name=VALUES(commercial_name);

-- 3. SEED BATCHES (10 Batches: Exactly 1 Expired, 2 Expiring within 30 days, 7 Active)
INSERT INTO batches (batch_number, medicine_id, manufacturing_date, expiry_date, total_units_produced, recall_status) VALUES
-- ACTIVE BATCH 1
('BCH-PCM-9042', 101, DATE_SUB(CURDATE(), INTERVAL 180 DAY), DATE_ADD(CURDATE(), INTERVAL 365 DAY), 50000, 'ACTIVE'),
-- EXPIRING SOON BATCH 1 (Expires in 25 days)
('BCH-PCM-9043', 101, DATE_SUB(CURDATE(), INTERVAL 340 DAY), DATE_ADD(CURDATE(), INTERVAL 25 DAY), 40000, 'ACTIVE'),
-- ACTIVE BATCH 2
('BCH-NRC-1011', 102, DATE_SUB(CURDATE(), INTERVAL 120 DAY), DATE_ADD(CURDATE(), INTERVAL 400 DAY), 30000, 'ACTIVE'),
-- ACTIVE BATCH 3
('BCH-NRC-1012', 102, DATE_SUB(CURDATE(), INTERVAL 90 DAY),  DATE_ADD(CURDATE(), INTERVAL 450 DAY), 25000, 'ACTIVE'),
-- ACTIVE BATCH 4
('BCH-GLU-5501', 103, DATE_SUB(CURDATE(), INTERVAL 150 DAY), DATE_ADD(CURDATE(), INTERVAL 500 DAY), 60000, 'ACTIVE'),
-- EXPIRED BATCH 1 (Expired 30 days ago)
('BCH-GLU-5502', 103, DATE_SUB(CURDATE(), INTERVAL 730 DAY), DATE_SUB(CURDATE(), INTERVAL 30 DAY), 45000, 'EXPIRED'),
-- ACTIVE BATCH 5
('BCH-PLM-3301', 104, DATE_SUB(CURDATE(), INTERVAL 60 DAY),  DATE_ADD(CURDATE(), INTERVAL 600 DAY), 20000, 'ACTIVE'),
-- ACTIVE BATCH 6
('BCH-GST-7701', 105, DATE_SUB(CURDATE(), INTERVAL 100 DAY), DATE_ADD(CURDATE(), INTERVAL 400 DAY), 35000, 'ACTIVE'),
-- EXPIRING SOON BATCH 2 (Expires in 12 days)
('BCH-GST-7702', 105, DATE_SUB(CURDATE(), INTERVAL 350 DAY), DATE_ADD(CURDATE(), INTERVAL 12 DAY), 28000, 'ACTIVE'),
-- ACTIVE BATCH 7
('BCH-DER-8801', 106, DATE_SUB(CURDATE(), INTERVAL 45 DAY),  DATE_ADD(CURDATE(), INTERVAL 700 DAY), 15000, 'ACTIVE')
ON DUPLICATE KEY UPDATE 
    manufacturing_date=VALUES(manufacturing_date),
    expiry_date=VALUES(expiry_date),
    recall_status=VALUES(recall_status);

-- 4. SEED HOSPITALS (4 Hospitals)
INSERT INTO hospitals (hospital_id, hospital_name, city, state, contact_phone) VALUES
(1, 'St. Jude Memorial Hospital', 'Metropolis', 'NY', '+1-212-555-0199'),
(2, 'City General Hospital', 'Chicago', 'IL', '+1-312-555-0144'),
(3, 'Parkland Health Center', 'Dallas', 'TX', '+1-214-555-0177'),
(4, 'Pacific Crest Medical Center', 'Seattle', 'WA', '+1-206-555-0122')
ON DUPLICATE KEY UPDATE hospital_name=VALUES(hospital_name);

-- 5. SEED BATCH_DISTRIBUTION (15 Distribution Rows)
INSERT INTO batch_distribution (distribution_id, batch_number, hospital_id, quantity_delivered, dispatch_date) VALUES
(1, 'BCH-PCM-9042', 1, 12000, DATE_SUB(CURDATE(), INTERVAL 150 DAY)),
(2, 'BCH-PCM-9042', 2, 8500,  DATE_SUB(CURDATE(), INTERVAL 140 DAY)),
(3, 'BCH-PCM-9042', 3, 14000, DATE_SUB(CURDATE(), INTERVAL 130 DAY)),
(4, 'BCH-PCM-9043', 2, 9000,  DATE_SUB(CURDATE(), INTERVAL 300 DAY)),
(5, 'BCH-PCM-9043', 4, 11000, DATE_SUB(CURDATE(), INTERVAL 280 DAY)),
(6, 'BCH-NRC-1011', 1, 6000,  DATE_SUB(CURDATE(), INTERVAL 100 DAY)),
(7, 'BCH-NRC-1011', 4, 7500,  DATE_SUB(CURDATE(), INTERVAL 90 DAY)),
(8, 'BCH-NRC-1012', 3, 5000,  DATE_SUB(CURDATE(), INTERVAL 75 DAY)),
(9, 'BCH-GLU-5501', 1, 15000, DATE_SUB(CURDATE(), INTERVAL 120 DAY)),
(10, 'BCH-GLU-5501', 2, 18000, DATE_SUB(CURDATE(), INTERVAL 110 DAY)),
(11, 'BCH-GLU-5502', 3, 10000, DATE_SUB(CURDATE(), INTERVAL 700 DAY)),
(12, 'BCH-PLM-3301', 4, 4500,  DATE_SUB(CURDATE(), INTERVAL 50 DAY)),
(13, 'BCH-GST-7701', 1, 8000,  DATE_SUB(CURDATE(), INTERVAL 80 DAY)),
(14, 'BCH-GST-7702', 2, 7000,  DATE_SUB(CURDATE(), INTERVAL 320 DAY)),
(15, 'BCH-DER-8801', 3, 3500,  DATE_SUB(CURDATE(), INTERVAL 30 DAY))
ON DUPLICATE KEY UPDATE quantity_delivered=VALUES(quantity_delivered);

-- 6. SEED USERS (Bcrypt Hashed Passwords for RBAC)
-- Passwords:
-- doctor_smith -> doctor123
-- pharmacist_jane -> pharmacist123
-- admin_officer -> admin123
INSERT INTO users (user_id, username, password_hash, role, full_name, email) VALUES
(1, 'doctor_smith', '$2b$12$bW9qDlpA2uMa7O9HHEqXiOh8GRYZSdZPvQBiG2WvP/8rhQ0PD74qy', 'DOCTOR_PATIENT', 'Dr. Sarah Smith, MD', 'dr.smith@stjudehospital.org'),
(2, 'pharmacist_jane', '$2b$12$v8Omcdxca1H3G1hlBK/OrO9h.4pqXZo06z8eY2mBbbpdmu8YgvqVG', 'PHARMACIST', 'Jane Doe, PharmD', 'jane.doe@centralpharmacy.com'),
(3, 'admin_officer', '$2b$12$cl/8mQTZKdZrsu51G.LrXO/PUNbwCPsM47CyI/eiybtoCSwZ5I97i', 'SAFETY_OFFICER_ADMIN', 'Chief Safety Officer Miller', 'compliance@pharmavigil.gov')
ON DUPLICATE KEY UPDATE role=VALUES(role);
