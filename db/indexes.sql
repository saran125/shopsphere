USE shopsphere;
CREATE INDEX idx_products_category_active ON Products(category_id, is_active);
CREATE INDEX idx_products_seller ON Products(seller_id);
CREATE INDEX idx_orders_customer_date ON Orders(user_id, created_at);
CREATE INDEX idx_order_items_seller ON OrderItems(seller_id);
