"""Deterministic synthetic Olist-shaped data for quick local runs and tests."""
from __future__ import annotations

import datetime as dt
import random

CATEGORIES = {
    "beleza_saude": "health_beauty",
    "informatica_acessorios": "computers_accessories",
    "cama_mesa_banho": "bed_bath_table",
    "esporte_lazer": "sports_leisure",
    "brinquedos": "toys",
    "telefonia": "telephony",
}
STATES = ["SP", "RJ", "MG", "RS", "PR", "BA"]
CITIES = {"SP": "sao paulo", "RJ": "rio de janeiro", "MG": "belo horizonte",
          "RS": "porto alegre", "PR": "curitiba", "BA": "salvador"}
STATUSES = ["delivered"] * 18 + ["shipped", "canceled"]
PAYMENTS = ["credit_card"] * 6 + ["boleto"] * 3 + ["voucher"]


def load_sample(conn, n_orders: int = 300, seed: int = 42) -> None:
    rnd = random.Random(seed)
    cur = conn.cursor()

    cur.executemany(
        "INSERT INTO product_category_translation VALUES (%s, %s)", list(CATEGORIES.items())
    )
    sellers = [(f"s{i:03d}", "01000", CITIES[st], st) for i, st in
               enumerate(rnd.choices(STATES, k=8))]
    cur.executemany("INSERT INTO sellers VALUES (%s, %s, %s, %s)", sellers)

    cats = list(CATEGORIES)
    products = [(f"p{i:03d}", rnd.choice(cats), 40, 300, 2, rnd.randint(100, 3000), 20, 10, 15)
                for i in range(40)]
    cur.executemany("INSERT INTO products VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", products)

    customers = []
    for i in range(120):
        st = rnd.choice(STATES)
        customers.append((f"c{i:04d}", f"u{i:04d}", "01000", CITIES[st], st))
    cur.executemany("INSERT INTO customers VALUES (%s,%s,%s,%s,%s)", customers)

    start = dt.datetime(2017, 1, 1)
    orders, items, payments, reviews = [], [], [], []
    for n in range(n_orders):
        oid = f"o{n:05d}"
        cust = rnd.choice(customers)[0]
        status = rnd.choice(STATUSES)
        purchase = start + dt.timedelta(days=rnd.randint(0, 600), hours=rnd.randint(0, 23))
        delivered = purchase + dt.timedelta(days=rnd.randint(3, 25)) if status == "delivered" else None
        estimated = purchase + dt.timedelta(days=rnd.randint(10, 25))
        orders.append((oid, cust, status, purchase, purchase + dt.timedelta(hours=1),
                       purchase + dt.timedelta(days=2) if status != "canceled" else None,
                       delivered, estimated))
        total = 0.0
        for k in range(1, rnd.randint(1, 3) + 1):
            price = round(rnd.uniform(10, 300), 2)
            freight = round(rnd.uniform(5, 40), 2)
            total += price + freight
            items.append((oid, k, rnd.choice(products)[0], rnd.choice(sellers)[0],
                          purchase + dt.timedelta(days=3), price, freight))
        payments.append((oid, 1, rnd.choice(PAYMENTS), rnd.randint(1, 10), round(total, 2)))
        if status == "delivered":
            reviews.append((f"r{n:05d}", oid, rnd.choice([5, 5, 5, 4, 4, 3, 2, 1]), None, None,
                            delivered, delivered + dt.timedelta(days=1)))

    cur.executemany("INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", orders)
    cur.executemany("INSERT INTO order_items VALUES (%s,%s,%s,%s,%s,%s,%s)", items)
    cur.executemany("INSERT INTO order_payments VALUES (%s,%s,%s,%s,%s)", payments)
    cur.executemany("INSERT INTO order_reviews VALUES (%s,%s,%s,%s,%s,%s,%s)", reviews)
