USE nasa_food_inventory;

-- =========================================
-- USERS
-- =========================================

INSERT INTO users (name, email, password, role) VALUES
('System Administrator', 'admin@isrofood.com', 'pbkdf2:sha256:600000$s0JfD3cczv0vGKOJrxo47g$c2cc3bf3db5ca17579008a492b300ac65bd5d6daf5c2b024b391c45440cb1ac5', 'Admin'),
('Inventory Manager', 'manager@isrofood.com', 'pbkdf2:sha256:600000$YxQPbv2Y_mIpLxFX_eMBJA$cd69c470e5a626927686db15535177956b19e9a5d8ea9492023cb5d6deeb5efd', 'Manager'),
('Mission Staff', 'staff@isrofood.com', 'pbkdf2:sha256:600000$qz5ymktRoPppTkSh23GHOQ$0cbdb40f8bffb4b0958aa0c0091ab02f563a2a3bca428da64062fdc45ff59dcf', 'Staff');


-- =========================================
-- FOOD CATEGORIES
-- =========================================

INSERT INTO food_categories (category_name, description) VALUES
('Main Meals', 'Ready-to-eat and specially packaged Indian meals'),
('Snacks', 'Energy-rich packaged snacks'),
('Fruits', 'Dehydrated and processed fruits'),
('Beverages', 'Powdered and instant beverages'),
('Desserts', 'Long shelf-life Indian desserts');


-- =========================================
-- SUPPLIERS
-- =========================================

INSERT INTO suppliers
(supplier_name, contact_person, phone, email, address)
VALUES
('Bharat Space Nutrition Systems', 'Arun Kumar',
 '9876501001', 'contact@bsns.example', 'Bengaluru, Karnataka'),

('Indian Space Food Research Centre', 'Priya Sharma',
 '9876501002', 'research@isfrc.example', 'Bengaluru, Karnataka'),

('Orbital Foods India', 'Rahul Menon',
 '9876501003', 'info@orbitalfoods.example', 'Hyderabad, Telangana'),

('Aero Nutrition Technologies', 'Meera Iyer',
 '9876501004', 'support@aeronutrition.example', 'Chennai, Tamil Nadu');


-- =========================================
-- FOOD ITEMS
-- =========================================

INSERT INTO food_items
(food_name, category_id, supplier_id, calories, protein, carbs, fat, unit, expiry_date)
VALUES

('Dehydrated Vegetable Rice', 1, 1,
 350, 8, 72, 4, 'packet', '2028-06-15'),

('Ready-to-Eat Sambar Rice', 1, 2,
 320, 9, 60, 6, 'packet', '2028-08-20'),

('Dehydrated Lemon Rice', 1, 1,
 300, 7, 58, 5, 'packet', '2028-05-10'),

('Ready-to-Eat Vegetable Upma', 1, 3,
 280, 8, 48, 7, 'packet', '2028-07-25'),

('Indian Spice Energy Bar', 2, 3,
 210, 8, 28, 7, 'bar', '2028-03-15'),

('Peanut Chikki', 2, 4,
 190, 6, 22, 9, 'bar', '2028-04-20'),

('Dehydrated Mango Pack', 3, 2,
 120, 2, 27, 1, 'pack', '2028-02-28'),

('Dehydrated Banana Pack', 3, 4,
 130, 2, 30, 1, 'pack', '2028-05-30'),

('Instant Filter Coffee', 4, 3,
 60, 2, 10, 1, 'packet', '2028-10-15'),

('Masala Tea Mix', 4, 1,
 70, 1, 13, 1, 'packet', '2028-09-20'),

('Instant Badam Milk Mix', 4, 2,
 150, 5, 18, 6, 'packet', '2028-11-15'),

('Mysore Pak', 5, 4,
 200, 3, 22, 12, 'pack', '2028-01-30');


-- =========================================
-- INVENTORY
-- =========================================

INSERT INTO inventory
(food_id, quantity, reorder_level, storage_location)
VALUES

(1, 500, 100, 'ISRO Food Storage - A'),
(2, 400, 100, 'ISRO Food Storage - A'),
(3, 350, 75, 'ISRO Food Storage - A'),
(4, 300, 75, 'ISRO Food Storage - B'),
(5, 600, 150, 'ISRO Food Storage - B'),
(6, 450, 100, 'ISRO Food Storage - B'),
(7, 250, 75, 'ISRO Food Storage - C'),
(8, 300, 75, 'ISRO Food Storage - C'),
(9, 500, 100, 'ISRO Food Storage - C'),
(10, 450, 100, 'ISRO Food Storage - D'),
(11, 200, 50, 'ISRO Food Storage - D'),
(12, 40, 75, 'ISRO Food Storage - D');


-- =========================================
-- SAMPLE MISSIONS
-- =========================================

INSERT INTO missions
(mission_name, mission_type, launch_date, duration_days, crew_size, status)
VALUES

('Gaganyaan Test Mission-01', 'Crewed Orbital Mission',
 '2027-05-15', 7, 3, 'Planned'),

('Bharat Orbital Research Mission', 'Orbital Research Mission',
 '2027-09-10', 30, 4, 'Planned'),

('Lunar Food Technology Mission', 'Lunar Research Mission',
 '2028-03-20', 45, 4, 'Planned');


-- =========================================
-- ASTRONAUTS / CREW
-- =========================================

INSERT INTO astronauts
(astronaut_name, mission_id, role)
VALUES

('Arjun Nair', 1, 'Mission Commander'),
('Vikram Rao', 1, 'Pilot'),
('Aditya Menon', 1, 'Mission Specialist'),

('Rohan Sharma', 2, 'Mission Commander'),
('Kiran Iyer', 2, 'Pilot'),
('Neha Kapoor', 2, 'Science Specialist'),
('Siddharth Das', 2, 'Mission Specialist'),

('Aarav Krishnan', 3, 'Mission Commander'),
('Ananya Patel', 3, 'Science Specialist'),
('Rahul Verma', 3, 'Pilot'),
('Meera Nair', 3, 'Mission Specialist');


-- =========================================
-- FOOD ALLOCATION
-- =========================================

INSERT INTO food_allocation
(mission_id, food_id, astronaut_id, quantity, allocation_date)
VALUES

-- Gaganyaan Test Mission-01

(1, 1, 1, 20, '2027-04-20'),
(1, 2, 1, 15, '2027-04-20'),
(1, 5, 2, 20, '2027-04-20'),
(1, 9, 3, 15, '2027-04-20'),

-- Bharat Orbital Research Mission

(2, 1, 4, 40, '2027-08-15'),
(2, 2, 5, 35, '2027-08-15'),
(2, 4, 6, 30, '2027-08-15'),
(2, 6, 7, 25, '2027-08-15'),

-- Lunar Food Technology Mission

(3, 3, 8, 50, '2028-02-15'),
(3, 4, 9, 40, '2028-02-15'),
(3, 7, 10, 30, '2028-02-15'),
(3, 11, 11, 25, '2028-02-15');


-- =========================================
-- STOCK TRANSACTIONS
-- =========================================

INSERT INTO stock_transactions
(food_id, transaction_type, quantity, remarks)
VALUES

(1, 'IN', 500, 'Initial food stock received'),
(2, 'IN', 400, 'Initial food stock received'),
(3, 'IN', 350, 'Initial food stock received'),
(4, 'IN', 300, 'Initial food stock received'),
(5, 'IN', 600, 'Initial food stock received'),
(6, 'IN', 450, 'Initial food stock received'),
(7, 'IN', 250, 'Initial food stock received'),
(8, 'IN', 300, 'Initial food stock received'),
(9, 'IN', 500, 'Initial food stock received'),
(10, 'IN', 450, 'Initial food stock received'),
(11, 'IN', 200, 'Initial food stock received'),
(12, 'IN', 40, 'Initial food stock received'),

(1, 'OUT', 20, 'Allocated to Gaganyaan Test Mission-01'),
(2, 'OUT', 15, 'Allocated to Gaganyaan Test Mission-01'),
(5, 'OUT', 20, 'Allocated to Gaganyaan Test Mission-01'),

(12, 'WASTAGE', 5, 'Packaging damage during storage');