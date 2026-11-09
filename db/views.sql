USE shopsphere;
CREATE OR REPLACE VIEW sales_by_category AS
SELECT c.name category, SUM(oi.quantity * oi.unit_price) revenue, SUM(oi.quantity) units
FROM OrderItems oi JOIN Products p USING(product_id) JOIN Categories c USING(category_id)
GROUP BY c.category_id, c.name;
CREATE OR REPLACE VIEW low_stock_products AS
SELECT p.product_id, p.name, i.quantity, i.reorder_level
FROM Products p JOIN Inventory i USING(product_id) WHERE i.quantity <= i.reorder_level;
