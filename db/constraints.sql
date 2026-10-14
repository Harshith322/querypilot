-- Applied after loading. NOT VALID so slightly dirty real data does not block the load,
-- while the relationships still show up in schema introspection.
ALTER TABLE orders ADD FOREIGN KEY (customer_id) REFERENCES customers (customer_id) NOT VALID;
ALTER TABLE order_items ADD FOREIGN KEY (order_id) REFERENCES orders (order_id) NOT VALID;
ALTER TABLE order_items ADD FOREIGN KEY (product_id) REFERENCES products (product_id) NOT VALID;
ALTER TABLE order_items ADD FOREIGN KEY (seller_id) REFERENCES sellers (seller_id) NOT VALID;
ALTER TABLE order_payments ADD FOREIGN KEY (order_id) REFERENCES orders (order_id) NOT VALID;
ALTER TABLE order_reviews ADD FOREIGN KEY (order_id) REFERENCES orders (order_id) NOT VALID;
ALTER TABLE products ADD FOREIGN KEY (product_category_name)
  REFERENCES product_category_translation (product_category_name) NOT VALID;
