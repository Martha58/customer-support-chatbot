from fastapi_app.db_conn import Base
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, TIMESTAMP, DECIMAL

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, index=True)
    hashed_password = Column(String)

class CreateUser(BaseModel):
    username: str 
    email: str
    password: str

class ChatInput(BaseModel):
    user_message: str
    token: Optional[str] = None

# For AI agent
class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    email = Column(String, index=True, unique=True)
    phone_number= Column(String, index=True)
    gender= Column(String, index=True)
    date_of_birth = Column(DateTime, index=True)
    address = Column(String, index=True)
    city = Column(String, index=True)
    state = Column(String, index=True)
    country = Column(String, index=True)
    postal_code = Column(String, index=True)
    registration_date = Column(DateTime, index=True)
    loyalty_status = Column(String, index=True)

    # Relationships
    orders = relationship("Order", back_populates="customer")
    deliveries = relationship("Delivery", back_populates="customer")

class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False, index=False)
    description = Column(String, index=True)
    category = Column(String, nullable=False, index=False)
    brand = Column(String, index=True)
    price_usd = Column(DECIMAL(12, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    rating = Column(DECIMAL(2, 1))
    warranty_months = Column(DECIMAL(12, 2), nullable=False)
    created_at = Column(TIMESTAMP)

    # Relationship
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False, index=True)
    customer_name = Column(String, index=True)
    customer_email = Column(String, index=True)
    customer_phone = Column(String, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, index=True)
    product_name = Column(String, index=True)
    category = Column(String, index=True)
    quantity = Column(Integer, nullable=False, index=True) 
    unit_price_usd = Column(DECIMAL(12, 2), nullable=False)
    total_amount_usd = Column(DECIMAL(12, 2), nullable=False) 
    payment_method = Column(String, index=True)
    order_status = Column(String, index=True)
    shipping_address = Column(String, index=True)
    shipping_city = Column(String, index=True)
    shipping_state = Column(String, index=True)
    shipping_country = Column(String, index=True)
    order_date = Column(TIMESTAMP)

    # Relationship
    product = relationship("Product", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    deliveries = relationship("Delivery", back_populates="order")

class Delivery(Base):
    __tablename__ = "deliveries"

    delivery_id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    delivery_status = Column(String(50), nullable=True)
    current_state = Column(String(100), nullable=True)
    estimated_delivery_date = Column(TIMESTAMP, nullable=True)
    delivered_date = Column(TIMESTAMP, nullable=True)
    dispatch_company = Column(String(100), nullable=True)
    dispatch_contact = Column(String(50), nullable=True)
    tracking_id = Column(String(50), unique=True, nullable=True)
    delivery_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="deliveries")
    customer = relationship("Customer", back_populates="deliveries")