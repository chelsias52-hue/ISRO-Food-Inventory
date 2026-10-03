CREATE DATABASE IF NOT EXISTS nasa_food_inventory;

USE nasa_food_inventory;

-- 1. Users
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'Staff'
);

-- 2. Food Categories
CREATE TABLE food_categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 3. Suppliers
CREATE TABLE suppliers (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    supplier_name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    address VARCHAR(255)
);

-- 4. Food Items
CREATE TABLE food_items (
    food_id INT PRIMARY KEY AUTO_INCREMENT,
    food_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    supplier_id INT NOT NULL,
    calories DECIMAL(8,2),
    protein DECIMAL(8,2),
    carbs DECIMAL(8,2),
    fat DECIMAL(8,2),
    unit VARCHAR(50),
    expiry_date DATE,

    FOREIGN KEY (category_id)
        REFERENCES food_categories(category_id),

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id),

    INDEX idx_food_items_expiry_date (expiry_date)
);

-- 5. Inventory
CREATE TABLE inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    food_id INT NOT NULL UNIQUE,
    quantity INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 10,
    storage_location VARCHAR(100),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (food_id)
        REFERENCES food_items(food_id),

    CONSTRAINT chk_inventory_quantity_nonnegative CHECK (quantity >= 0),
    CONSTRAINT chk_inventory_reorder_nonnegative CHECK (reorder_level >= 0)
);

-- 6. Missions
CREATE TABLE missions (
    mission_id INT PRIMARY KEY AUTO_INCREMENT,
    mission_name VARCHAR(150) NOT NULL,
    mission_type VARCHAR(100),
    launch_date DATE,
    duration_days INT,
    crew_size INT,
    status VARCHAR(50) DEFAULT 'Planned',
    CONSTRAINT chk_missions_duration_positive
        CHECK (duration_days IS NULL OR duration_days > 0),
    CONSTRAINT chk_missions_crew_positive
        CHECK (crew_size IS NULL OR crew_size > 0),
    INDEX idx_missions_status_launch_date (status, launch_date)
);

-- 7. Astronauts
CREATE TABLE astronauts (
    astronaut_id INT PRIMARY KEY AUTO_INCREMENT,
    astronaut_name VARCHAR(100) NOT NULL,
    mission_id INT NOT NULL,
    role VARCHAR(100),

    FOREIGN KEY (mission_id)
        REFERENCES missions(mission_id)
);

-- 8. Food Allocation
CREATE TABLE food_allocation (
    allocation_id INT PRIMARY KEY AUTO_INCREMENT,
    mission_id INT NOT NULL,
    food_id INT NOT NULL,
    astronaut_id INT NOT NULL,
    quantity INT NOT NULL,
    allocation_date DATE NOT NULL,

    FOREIGN KEY (mission_id)
        REFERENCES missions(mission_id),

    FOREIGN KEY (food_id)
        REFERENCES food_items(food_id),

    FOREIGN KEY (astronaut_id)
        REFERENCES astronauts(astronaut_id),

    CONSTRAINT chk_food_allocation_quantity_positive
        CHECK (quantity > 0),
    INDEX idx_food_allocation_date (allocation_date)
);

-- 9. Stock Transactions
CREATE TABLE stock_transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    food_id INT NOT NULL,
    transaction_type ENUM('IN', 'OUT', 'RETURN', 'WASTAGE') NOT NULL,
    quantity INT NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255),

    FOREIGN KEY (food_id)
        REFERENCES food_items(food_id),

    CONSTRAINT chk_stock_transaction_quantity_positive
        CHECK (quantity > 0),
    INDEX idx_stock_transactions_date_type (transaction_date, transaction_type)
);