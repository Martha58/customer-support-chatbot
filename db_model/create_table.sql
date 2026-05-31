CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50),
    gender VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    registration_date DATE,
    loyalty_status VARCHAR(50)
);

CREATE TABLE products (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    price_usd DECIMAL(12,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    rating DECIMAL(2,1),
    warranty_months INT DEFAULT 0,
    created_at TIMESTAMP
);

CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL,
	customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    product_id VARCHAR(20) NOT NULL,
    product_name VARCHAR(255),
    category VARCHAR(100),
    quantity INT NOT NULL,
    unit_price_usd DECIMAL(12,2) NOT NULL,
    total_amount_usd DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(50),
    order_status VARCHAR(50),
    shipping_address TEXT,
    shipping_city VARCHAR(100),
    shipping_state VARCHAR(100),
    shipping_country VARCHAR(100),
    order_date TIMESTAMP,

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT fk_orders_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

CREATE TABLE deliveries (
    delivery_id VARCHAR(20) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL,
    customer_id VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    delivery_status VARCHAR(50),
    current_state VARCHAR(100),
    estimated_delivery_date TIMESTAMP,
    delivered_date TIMESTAMP,
    dispatch_company VARCHAR(100),
    dispatch_contact VARCHAR(50),

    tracking_id VARCHAR(50) UNIQUE,

    delivery_address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),

    CONSTRAINT fk_delivery_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT fk_delivery_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

CREATE TABLE enquiry (
    id uuid primary key default gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(50),
    enquiry_message Text,
    enquiry_reason VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);