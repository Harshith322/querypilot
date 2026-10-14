import psycopg
import pytest

from scripts.load_csv import FILES, load_csv_dir


@pytest.fixture
def restore_sample(db):
    yield
    from scripts.init_db import init_db

    init_db(db["admin"], sample=True)  # this test recreates tables, so restore shared state


def test_load_csv_dir_with_tiny_files(db, tmp_path, restore_sample):
    from scripts.init_db import DB_DIR

    with psycopg.connect(db["admin"], autocommit=True) as conn:
        conn.execute((DB_DIR / "schema.sql").read_text())  # empty tables
        data = {
            "olist_customers_dataset.csv": "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state\nc1,u1,14409,franca,SP\n",
            "olist_sellers_dataset.csv": "seller_id,seller_zip_code_prefix,seller_city,seller_state\ns1,13023,campinas,SP\n",
            "product_category_name_translation.csv": "product_category_name,product_category_name_english\nperfumaria,perfumery\n",
            "olist_products_dataset.csv": "product_id,product_category_name,product_name_lenght,product_description_lenght,product_photos_qty,product_weight_g,product_length_cm,product_height_cm,product_width_cm\np1,perfumaria,40,287,1,225,16,10,14\np2,,,,,,,,\n",
            "olist_orders_dataset.csv": "order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date\no1,c1,canceled,2018-01-01 10:00:00,,,,2018-02-01 00:00:00\n",
            "olist_order_items_dataset.csv": "order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value\no1,1,p1,s1,2018-01-05 10:00:00,29.99,8.72\n",
            "olist_order_payments_dataset.csv": "order_id,payment_sequential,payment_type,payment_installments,payment_value\no1,1,credit_card,2,38.71\n",
            "olist_order_reviews_dataset.csv": 'review_id,order_id,review_score,review_comment_title,review_comment_message,review_creation_date,review_answer_timestamp\nr1,o1,4,,"line one\nline two",2018-01-10 00:00:00,2018-01-11 00:00:00\n',
        }
        for name, text in data.items():
            (tmp_path / name).write_text(text)
        counts = load_csv_dir(conn, tmp_path)
        assert counts["orders"] == 1 and counts["products"] == 2
        assert counts["order_reviews"] == 1
        assert conn.execute("SELECT order_approved_at FROM orders").fetchone()[0] is None
        assert {f for f, _ in FILES} == set(data)
