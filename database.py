import aiosqlite

DB_NAME = "shop.db"


class Database:
    def __init__(self):
        self.db_name = DB_NAME

    async def create_tables(self):
        async with aiosqlite.connect(self.db_name) as db:
            # 1. Таблиця користувачів
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS users
                             (
                                 user_id
                                 INTEGER
                                 PRIMARY
                                 KEY,
                                 language
                                 TEXT
                                 DEFAULT
                                 'ua',
                                 currency
                                 TEXT
                                 DEFAULT
                                 'UAH'
                             )
                             """)

            # 2. Таблиця товарів
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS products
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 name
                                 TEXT
                                 NOT
                                 NULL,
                                 desc
                                 TEXT,
                                 price
                                 INTEGER
                                 NOT
                                 NULL,
                                 category
                                 TEXT
                                 DEFAULT
                                 'Інше'
                             )
                             """)
            # 3. Таблиця кошика
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS cart
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 user_id
                                 INTEGER
                                 NOT
                                 NULL,
                                 product_id
                                 INTEGER
                                 NOT
                                 NULL,
                                 quantity
                                 INTEGER
                                 DEFAULT
                                 1,
                                 FOREIGN
                                 KEY
                             (
                                 product_id
                             ) REFERENCES products
                             (
                                 id
                             )
                                 )
                             """)
            # 4. Таблиця замовлень
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS orders
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 user_id
                                 INTEGER
                                 NOT
                                 NULL,
                                 user_name
                                 TEXT,
                                 user_phone
                                 TEXT,
                                 user_address
                                 TEXT,
                                 delivery_method
                                 TEXT,
                                 items_text
                                 TEXT,
                                 total_price
                                 REAL,
                                 currency_code
                                 TEXT,
                                 status
                                 TEXT
                                 DEFAULT
                                 'pending',
                                 created_at
                                 TIMESTAMP
                                 DEFAULT
                                 CURRENT_TIMESTAMP
                             )
                             """)

            # Тестові дані (Розширений список)
            async with db.execute("SELECT count(*) FROM products") as cursor:
                count = await cursor.fetchone()
                if count[0] == 0:
                    products = [
                        # Laptops
                        ("MacBook Pro 16", "M3 Max, 32GB RAM", 95000, "Laptops"),
                        ("Asus ROG Strix", "RTX 4070, i9", 75000, "Laptops"),
                        ("Lenovo Legion 5", "RTX 4060, Ryzen 7", 55000, "Laptops"),
                        ("Dell XPS 15", "OLED 3.5K, i7", 85000, "Laptops"),
                        ("HP Spectre x360", "Convertible, i7", 60000, "Laptops"),

                        # Smartphones
                        ("iPhone 15 Pro", "Titanium, 256GB", 48000, "Smartphones"),
                        ("Samsung S24 Ultra", "AI Phone, 512GB", 52000, "Smartphones"),
                        ("Google Pixel 8 Pro", "Pure Android, 128GB", 35000, "Smartphones"),
                        ("Xiaomi 14", "Leica Optics", 30000, "Smartphones"),
                        ("Sony Xperia 1 V", "For Creators", 42000, "Smartphones"),

                        # Tablets
                        ("iPad Air 5", "M1 Chip, 64GB", 25000, "Tablets"),
                        ("Samsung Tab S9", "AMOLED, S-Pen", 32000, "Tablets"),
                        ("Lenovo Tab P11", "Budget Choice", 12000, "Tablets"),

                        # Accessories
                        ("AirPods Pro 2", "USB-C Case", 11000, "Accessories"),
                        ("Apple Watch S9", "Midnight Aluminum", 19000, "Accessories"),
                        ("Galaxy Watch 6", "Classic Design", 14000, "Accessories"),
                        ("Sony WH-1000XM5", "Noise Cancelling", 16000, "Accessories"),
                        ("PowerBank 20k", "Fast Charge 65W", 2500, "Accessories")
                    ]
                    await db.executemany(
                        "INSERT INTO products (name, desc, price, category) VALUES (?, ?, ?, ?)",
                        products
                    )

            await db.commit()

    # --- КОРИСТУВАЧІ ---
    async def add_user(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def set_user_language(self, user_id: int, lang: str):
        """Встановлює мову. Якщо користувача немає — створює його."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()

            if exists:
                await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
            else:
                await db.execute("INSERT INTO users (user_id, language, currency) VALUES (?, ?, 'UAH')",
                                 (user_id, lang))
            await db.commit()

    async def get_user_settings(self, user_id: int):
        """Повертає мову та валюту користувача"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT language, currency FROM users WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                if res:
                    return res['language'], res['currency']
                return 'ua', 'UAH'

    async def set_user_currency(self, user_id: int, currency: str):
        """Встановлює валюту. Якщо користувача немає — створює його."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()

            if exists:
                await db.execute("UPDATE users SET currency = ? WHERE user_id = ?", (currency, user_id))
            else:
                await db.execute("INSERT INTO users (user_id, language, currency) VALUES (?, 'ua', ?)",
                                 (user_id, currency))
            await db.commit()

    # --- ТОВАРИ ---
    async def get_categories(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT DISTINCT category FROM products") as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def get_products_by_category(self, category: str):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products WHERE category = ?", (category,)) as cursor:
                return await cursor.fetchall()

    async def get_product(self, product_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
                return await cursor.fetchone()

    async def add_product(self, name: str, desc: str, price: int, category: str):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO products (name, desc, price, category) VALUES (?, ?, ?, ?)",
                             (name, desc, price, category))
            await db.commit()

    async def delete_product(self, product_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            await db.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
            await db.commit()

    async def get_all_products(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products") as cursor:
                return await cursor.fetchall()

    # --- КОШИК ---
    async def add_to_cart(self, user_id: int, product_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?",
                                      (user_id, product_id))
            item = await cursor.fetchone()

            if item:
                await db.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ?",
                                 (user_id, product_id))
            else:
                await db.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)",
                                 (user_id, product_id))
            await db.commit()

    async def get_cart(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                    SELECT c.id as cart_id, c.quantity, p.name, p.price, p.id as product_id
                    FROM cart c
                             JOIN products p ON c.product_id = p.id
                    WHERE c.user_id = ? \
                    """
            async with db.execute(query, (user_id,)) as cursor:
                return await cursor.fetchall()

    async def delete_from_cart(self, cart_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
            await db.commit()

    async def clear_cart(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
            await db.commit()

    # --- ЗАМОВЛЕННЯ ---
    async def add_order(self, data: dict):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("""
                                      INSERT INTO orders (user_id, user_name, user_phone, user_address, delivery_method,
                                                          items_text, total_price, currency_code, status)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                      """, (
                                          data['user_id'], data['user_name'], data['user_phone'], data['user_address'],
                                          data['delivery_method'], data['items_text'], data['total_price'],
                                          data['currency_code'], data['status']
                                      ))
            await db.commit()
            return cursor.lastrowid

    async def get_orders(self, limit=10):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
                return await cursor.fetchall()

    async def get_user_orders(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)) as cursor:
                return await cursor.fetchall()

    async def get_order(self, order_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
                return await cursor.fetchone()

    async def update_order_status(self, order_id: int, status: str):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            await db.commit()


db = Database()