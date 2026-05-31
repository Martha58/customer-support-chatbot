from langchain_openai import OpenAI
from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langgraph.checkpoint.memory import InMemorySaver
from dataclasses import dataclass
from langgraph.runtime import get_runtime
from langchain_core.tools import tool
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from loguru import logger
from dotenv import load_dotenv
import requests
import ast
import sys
import os

# Project Root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from db_model.models import Customer, Order

load_dotenv()

DB_URI = os.getenv("DB_URI")
API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "chatbot-faq"

# if not pc.has_index(index_name):
#     pc.create_index(
#         name=index_name,
#         dimension=1536,
#         metric="cosine",
#         spec=ServerlessSpec(cloud="aws", region="us-east-1"),
#     )

index = pc.Index(index_name)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = PineconeVectorStore(index=index, embedding=embeddings)

def db_conn():
    # Connect to db
    try:
        db = SQLDatabase.from_uri(DB_URI)
        logger.info("Connection successfull")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to db because of, {e}")
        return None
    
@dataclass
class RuntimeContext:
    db: SQLDatabase

# @dataclass
# class RuntimeContext:
#     db: Session

def runtime_context():
    # Extracts the DB object with a fallback
    try:
        runtime = get_runtime(RuntimeContext)
        database = runtime.context.db
        if database is None:
            raise ValueError("Database instance is missing from RuntimeContext")
    except Exception as e:
        logger.error(f"Runtime context error: {e}")
        return {"found": False, "message": "Internal error accessing database configuration."}
    return database

@tool
def get_customer_order_details(name: str):
    """
    Fetch customer details and all orders for a given customer name.
    Deterministic ORM-based tool (no SQL, no DB passed from LLM).
    """
    
    db = runtime_context()

    # Use the underlying SQLAlchemy engine inside LangChain for deterministic dictionary outputs
    engine = db._engine

    try:
        with engine.connect() as connection:
            # 2. Get customer safely using parameterized bindings
            customer_sql = text("SELECT customer_id, customer_name, email FROM customers WHERE customer_name = :name")
            customer_result = connection.execute(customer_sql, {"name": name}).mappings().first()
            
            if not customer_result:
                return {
                    "found": False,
                    "message": f"Customer '{name}' not found",
                    "customer": None,
                    "orders": []
                }

            c_id = customer_result["customer_id"]
            c_name = customer_result["customer_name"]
            c_email = customer_result["email"]

            # 3. Get orders safely using the retrieved customer ID
            orders_sql = text("""
                SELECT order_id, product_name, category, quantity, total_amount_usd, order_status, order_date 
                FROM "orders" 
                WHERE customer_id = :customer_id 
                ORDER BY order_date DESC
            """)
            orders_result = connection.execute(orders_sql, {"customer_id": c_id}).mappings().all()

            # 4. Format outputs safely into native JSON serializable types
            formatted_orders = [
                {
                    "order_id": o["order_id"],
                    "product_name": o["product_name"],
                    "category": o["category"],
                    "quantity": o["quantity"],
                    "total_amount_usd": float(o["total_amount_usd"]) if o["total_amount_usd"] is not None else 0.0,
                    "order_status": o["order_status"],
                    "order_date": str(o["order_date"]),
                }
                for o in orders_result
            ]

            return {
                "found": True,
                "customer": {
                    "customer_id": c_id,
                    "customer_name": c_name,
                    "email": c_email,
                },
                "orders_count": len(formatted_orders),
                "orders": formatted_orders
            }

    except Exception as db_error:
        logger.error(f"Database query execution failed: {db_error}")
        return {"found": False, "message": f"Database execution error: {str(db_error)}"}


# @tool
def get_delivery_details(name: str):
    """
    Fetch all details related to delivery for a given customer name.
    Deterministic ORM-based tool (no SQL, no DB passed from LLM).
    """

    db = runtime_context()

    engine = db._engine
    
    try:
        with engine.connect() as connection:
            # Get customer details
            customer_sql = text("""
                SELECT customer_id, customer_name, email 
                FROM customers
                WHERE customer_name = :name
            """)
            customer_result = connection.execute(customer_sql, {"name": name}).mappings().first()

            if not customer_result:
                return {
                    "found": False,
                    "message": f"Customer '{name}' not found",
                    "customer": None,
                    "orders": []
                }

            c_id = customer_result["customer_id"]
            c_name = customer_result["customer_name"]
            c_email = customer_result["email"]

            # Get delivery details
            delivery_sql = text("""
                SELECT delivery_id, order_id, customer_id, customer_name, delivery_status, current_state, estimated_delivery_date, delivered_date, dispatch_company, dispatch_contact, tracking_id
                FROM deliveries
                WHERE customer_name = :name
            """)

            delivery_result = connection.execute(delivery_sql, {"name": name}).mappings().all()
            
            # Format outputs safely into native JSON serializable types
            formatted_delivery = [
                {
                    "delivery_id": d["delivery_id"],
                    "order_id": d["order_id"],
                    "customer_id": d["customer_id"],
                    "customer_name": d["customer_name"],
                    "delivery_status": d["delivery_status"],
                    "current_state": d["current_state"],
                    "estimated_delivery_date": str(d["estimated_delivery_date"]), # float(d["total_amount_usd"]) if o["total_amount_usd"] is not None else 0.0,
                    "delivered_date": str(d["delivered_date"]),
                    "dispatch_company": d["dispatch_company"],
                    "dispatch_contact": d["dispatch_contact"],
                    "tracking_id": d["tracking_id"]
                }
                for d in delivery_result
            ]

            return {
                "found": True,
                "customer": {
                    "customer_id": c_id,
                    "customer_name": c_name,
                    "email": c_email,
                },
                "delivery_count": len(formatted_delivery),
                "delivery": formatted_delivery
            }

    except Exception as db_error:
        logger.error(f"Database query execution failed: {db_error}")
        return {"found": False, "message": f"Database execution error: {str(db_error)}"}
    
def get_product_details(name: str):
    """
    Fetch details of all available products. 
    Deterministic ORM-based tool (no SQL, no DB passed from LLM).
    """

    db = runtime_context()
    engine = db._engine

    try:
        with engine.connect() as connection:
            product_sql = text("""
                SELECT product_id, product_name, description, category, brand, price_usd, rating, warranty_months
                FROM products
            """)
            product_result = connection.execute(product_sql).mappings().all()

            formated_result = [
                {
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "description": p["description"],
                    "category": p["category"],
                    "brand": p["brand"],
                    "price_usd": float(p["price_usd"]),
                    "rating": float(p["rating"]),
                    "warranty_months": p["warranty_months"]
                    }
                    for p in product_result
            ]
            return {
                "found": True,
                "product": formated_result
            }
    except Exception as db_error:
        logger.error(f"Database query execution failed: {db_error}")
        return {"found": False, "message": f"Database execution error: {str(db_error)}"}
    
def update_delivery_address(name: str, order_id: str, new_address: str):
    """
    Updates customer delivery address when needed
    """
    db = runtime_context()
    engine = db._engine
    
    try:
        with engine.connect() as connection:
            update_query = text("""
                UPDATE deliveries
                SET delivery_address = :new_address
                WHERE customer_name = :name AND order_id = :order_id
            """)
            result = connection.execute(update_query, {
                "name": name,
                "order_id": order_id,
                "new_address": new_address
            })
            connection.commit()  
            
            if result.rowcount > 0:
                return {
                    "found": True,
                    "message": f"Successfully updated delivery address for order {order_id}"
                }
            else:
                return {
                    "found": False,
                    "message": f"No delivery found for customer '{name}' with order ID {order_id}"
                }
    except Exception as db_error:
        logger.error(f"Database query execution failed: {db_error}")
        return {"found": False, "message": f"Database execution error: {str(db_error)}"}
    
def send_email(complaint_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send email via backend point
    """
    # Your backend API endpoint (configure this)
    API_ENDPOINT = "http://127.0.0.1:8000/send-mail"  # Replace with your actual endpoint
    API_KEY = RESEND_API_KEY
    
    # Format the email content
    email_content = f"""
            Hello,

            A customer has just lodged a complaint. Here are the full details:

            Name: {complaint_data['name']}
            Email: {complaint_data['email']}
            Phone Number: {complaint_data['customer_number']}
            Complaint Reason: {complaint_data['reason']}
            Description:
            {complaint_data['description']}

            Please review and respond as soon as possible.

            Best regards,
            Customer Support System
            """
    
    # Prepare the payload for your backend API
    payload = {
        "to": ["marthafridayimoh@gmail.com"],  # Can be multiple recipients
        "subject": f"New Customer Complaint from {complaint_data.get('name', 'Customer')}",
        "content": email_content.strip(),
        "customer_email": complaint_data.get('email'),
        "customer_name": complaint_data.get('name'),
        "complaint_type": complaint_data.get('reason', 'general')
    }
    
    try:
        # Call your backend API
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": "Email sent successfully",
                "email_id": result.get('email_id')
            }
        else:
            logger.error(f"API returned error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "message": f"API error: {response.status_code} - {response.text}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call email API: {e}")
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }
    
def log_enquiry(name: str, email: str, phone_number: str, enquiry_message: str, enquiry_reason: str):
    """
    Logs customers complaint and enquire into the database
    """
    db = runtime_context()
    engine = db._engine

    try:
        with engine.connect() as conn:
            log_message = text("""
                INSERT INTO enquiry (name, email, phone_number, enquiry_message, enquiry_reason)
                VALUES (:name, :email, :phone_number, :enquiry_message, :enquiry_reason)
            """)
            conn.execute(log_message, {
                "name": name,
                "email": email,
                "phone_number": phone_number,
                "enquiry_message": enquiry_message,
                "enquiry_reason": enquiry_reason
            })
            conn.commit()

            if "complaint" in enquiry_reason.lower():
                complaint_data = {
                    "type": "complaint",
                    "name": name,
                    "email": email,
                    "customer_number": phone_number,
                    "reason": enquiry_reason,
                    "description": enquiry_message
                }

                email_result = send_email(complaint_data)
                
                # Log the email result for debugging
                logger.info(f"Email send result: {email_result}")

                return {
                    "found": True,
                    "type": "complaint",
                    "message": "Complaint logged and email notification sent",
                    "email_sent": email_result.get("success", False),
                    "complaint_data": complaint_data
                }
            
            return {
                "found": True,
                "message": "Enquiry logged successfully"
            }
            
    except Exception as db_error:
        logger.error(f"Database query execution failed: {db_error}")
        return {"found": False, "message": f"Database execution error: {str(db_error)}"}
    
def retrive_faq(query: str):
    """
    Retrives information to help answer a fequently asked questions.
    """
    retrieve_doc = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieve_doc
    )
    return serialized, retrieve_doc

# def create_compliant(customer_name: str, enquiry_reason: str, description: str):
#     """
#     Creates a structed complain 
#     """

    
def chatbot(SYSTEM_PROMPT):
    model = "openai:gpt-4o-mini"
    agent = create_agent(
        model=model,
        tools=[get_customer_order_details, get_delivery_details, get_product_details, 
               retrive_faq, log_enquiry, update_delivery_address],
        system_prompt=SYSTEM_PROMPT,
        context_schema=RuntimeContext,
        checkpointer=InMemorySaver()
    )

    return agent

