CREATE DATABASE IF NOT EXISTS shopsphere;
USE shopsphere;
CREATE TABLE IF NOT EXISTS Users (
 user_id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL, full_name VARCHAR(120) NOT NULL,
 role ENUM('customer','seller','admin') NOT NULL DEFAULT 'customer',
 is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Sellers (
 seller_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL UNIQUE,
 store_name VARCHAR(160) NOT NULL, description TEXT,
 FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
CREATE TABLE IF NOT EXISTS Categories (
 category_id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE,
 is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS Products (
 product_id INT AUTO_INCREMENT PRIMARY KEY, seller_id INT NOT NULL, category_id INT NOT NULL,
 name VARCHAR(200) NOT NULL, description TEXT NOT NULL, price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
 is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (seller_id) REFERENCES Sellers(seller_id), FOREIGN KEY (category_id) REFERENCES Categories(category_id)
);
CREATE TABLE IF NOT EXISTS Inventory (
 product_id INT PRIMARY KEY, quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
 reorder_level INT NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
 FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
CREATE TABLE IF NOT EXISTS CartItems (
 user_id INT NOT NULL, product_id INT NOT NULL, quantity INT NOT NULL CHECK (quantity > 0),
 PRIMARY KEY (user_id, product_id), FOREIGN KEY (user_id) REFERENCES Users(user_id),
 FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
CREATE TABLE IF NOT EXISTS Orders (
 order_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, status VARCHAR(30) DEFAULT 'paid',
 total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
CREATE TABLE IF NOT EXISTS OrderItems (
 order_item_id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, product_id INT NOT NULL,
 seller_id INT NOT NULL, quantity INT NOT NULL CHECK (quantity > 0), unit_price DECIMAL(10,2) NOT NULL,
 FOREIGN KEY (order_id) REFERENCES Orders(order_id), FOREIGN KEY (product_id) REFERENCES Products(product_id),
 FOREIGN KEY (seller_id) REFERENCES Sellers(seller_id)
);
CREATE TABLE IF NOT EXISTS Payments (
 payment_id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL UNIQUE, amount DECIMAL(10,2) NOT NULL,
 method VARCHAR(40) NOT NULL, status VARCHAR(30) DEFAULT 'simulated', paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (order_id) REFERENCES Orders(order_id)
);
