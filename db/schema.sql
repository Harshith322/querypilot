-- Olist Brazilian e-commerce schema (Kaggle). Column names mirror the CSV headers,
-- including the dataset's own spelling ("lenght").
DROP TABLE IF EXISTS order_reviews, order_payments, order_items, orders,
  products, product_category_translation, sellers, customers CASCADE;

CREATE TABLE customers (
  customer_id text PRIMARY KEY,
  customer_unique_id text,
  customer_zip_code_prefix text,
  customer_city text,
  customer_state text
);
CREATE TABLE sellers (
  seller_id text PRIMARY KEY,
  seller_zip_code_prefix text,
  seller_city text,
  seller_state text
);
CREATE TABLE product_category_translation (
  product_category_name text PRIMARY KEY,
  product_category_name_english text
);
CREATE TABLE products (
  product_id text PRIMARY KEY,
  product_category_name text,
  product_name_lenght numeric,
  product_description_lenght numeric,
  product_photos_qty numeric,
  product_weight_g numeric,
  product_length_cm numeric,
  product_height_cm numeric,
  product_width_cm numeric
);
CREATE TABLE orders (
  order_id text PRIMARY KEY,
  customer_id text,
  order_status text,
  order_purchase_timestamp timestamp,
  order_approved_at timestamp,
  order_delivered_carrier_date timestamp,
  order_delivered_customer_date timestamp,
  order_estimated_delivery_date timestamp
);
CREATE TABLE order_items (
  order_id text,
  order_item_id integer,
  product_id text,
  seller_id text,
  shipping_limit_date timestamp,
  price numeric(10,2),
  freight_value numeric(10,2),
  PRIMARY KEY (order_id, order_item_id)
);
CREATE TABLE order_payments (
  order_id text,
  payment_sequential integer,
  payment_type text,
  payment_installments integer,
  payment_value numeric(10,2),
  PRIMARY KEY (order_id, payment_sequential)
);
CREATE TABLE order_reviews (
  review_id text,
  order_id text,
  review_score integer,
  review_comment_title text,
  review_comment_message text,
  review_creation_date timestamp,
  review_answer_timestamp timestamp
);
