from fastapi import FastAPI, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from db_conn import SessionLocal, engine, Base
from auth_utils import create_access_token, hash_password, verify_password, decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from getuser import get_db, get_current_user
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, List, Any
from dotenv import load_dotenv
from pydantic import BaseModel
import resend
import sys
import os

# Project Root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from model.chatbot import db_conn, RuntimeContext, get_customer_order_details, chatbot
from db_model.models import User, CreateUser, ChatInput

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

Base.metadata.create_all(bind=engine)
app = FastAPI()
# security = HTTPBearer

SYSTEM_PROMPT = """
You are a customer support chatbot tasked with assisting both new and existing customers.

1. **User Authentication:**
   - First, check if the user is logged in.
   - If the user is **not logged in**, inform them that logging in is required for personalized responses. 
   - You may still answer frequently asked questions (FAQs) and general inquiries for non-logged-in users.
   
2. **Customer Classification:**
   - If the user is logged in, determine whether they are a **new** or **existing customer** by checking the `customers` database table.
   - If the customer exists in the database, they are an existing customer. If not, they are a new customer.
   - Note: Being logged in does not imply they have made any purchases.

3. **Interaction Guidelines:**
   - **Existing Customers:**  
     - Understand the reason for contact (complaint, order inquiry, delivery inquiry, or product question).  
     - Assist accordingly using their customer, delivery and order history.
   - **New Customers:**  
     - Understand their needs, check product availability, and recommend suitable products.  
     - Provide convincing suggestions to encourage purchases.
   
4. **Always make use of the retrive_faq tool for questions similar to what we have there.** 
   - Always determine the intent of the query first, if it is general inquiry related to fequently asked questions use the retrive_faq tool
   - Use retrive_faq tool to answer all enquiry and if you can't find the answer to customer's inquiry, tell them to reach out to support with the support mail in the faq doc

5. **Always ensure you determine the user intent:**
   - If it has to do with updating their information, make use of the update_delivery_address tool.
   
6. **HANDLING COMPLAINTS (CRITICAL):**
   - If it's a complaint, you MUST:
     a) Determine the reason (enquiry or complaint)
     b) Collect all necessary information: customer name, email, phone number, complaint reason, and description
     c) Call `log_enquiry` tool with ALL the collected information
     d) **IMMEDIATELY AFTER logging, call `send_email` tool** with the complaint data to notify the support team
     e) The `send_email` tool requires a dictionary with: name, email, customer_number, reason, description
   
   Example flow for complaint:
    Step 1: Ask for missing information if needed
    Step 2: Call log_enquiry(name, email, phone, message, reason)
    Step 3: Call send_email({"name": name, "email": email, "customer_number": phone, "reason": reason, "description": message})
    Step 4: Confirm to customer that complaint was logged and team will be notified
   NOTE: Only send out mail if the reason is Complaint, if not run retrive_faq tool to answer questions. 
        And if you are unable to find the answer ther, inform them to chat support using any mail found in the faq doc

7. **For general enquiries (not complaints):**
  - Log using `log_enquiry` tool without triggering email
"""

agent_db = db_conn()
agent = chatbot(SYSTEM_PROMPT)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

class EmailRequest(BaseModel):
    to: List[str]
    subject: str
    content: str
    customer_email: str = None  
    customer_name: str = None   
    complaint_type: str = None 

@app.post("/signup")
def signup(user: CreateUser, db: Session = Depends(get_db)):
    user_exist = db.query(User).filter(User.username == user.username).first()

    if user_exist:
        raise HTTPException(status_code=400, detail="User already exist")
    
    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"username": new_user.username, "id": new_user.id}

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    check_user = db.query(User).filter(
        User.username == form_data.username
    ).first()

    if not check_user or not verify_password(
        form_data.password,
        check_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": check_user.username}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email}

@app.post("/chatbot")
def chat_agent(
    request: ChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_context = "The user is NOT logged in. Answer only general FAQs."

    if current_user:
        user_context = (
            f"The user is LOGGED IN as {current_user.username} (Email: {current_user.email}). "
            "They are an existing customer. You may provide personalized responses."
        )

    user_thread_id = f"user_{current_user.id}" if current_user else "guest_session_123"

    messages = [
        SystemMessage(content=user_context),
        HumanMessage(content=request.user_message) 
    ]

    print(f"Messages: {messages}")

    try:
        for step in agent.stream(
            {"messages": messages}, 
            config={"configurable": {"thread_id": user_thread_id}},
            context=RuntimeContext(db=agent_db),
            stream_mode="values",
        ):
            step["messages"][-1].pretty_print()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-mail")
def send_mail(email_request: EmailRequest) -> Dict:
    """
    Send email using Resend
    """
    try:
        # Create HTML content with better formatting
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">New Customer Complaint</h2>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                <p><strong>Customer Name:</strong> {email_request.customer_name or 'Not provided'}</p>
                <p><strong>Customer Email:</strong> {email_request.customer_email or 'Not provided'}</p>
                <p><strong>Complaint Type:</strong> {email_request.complaint_type or 'General'}</p>
            </div>
            <h3>Complaint Details:</h3>
            <p style="white-space: pre-wrap;">{email_request.content}</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated notification from your Customer Support System.
            </p>
        </div>
        """
        
        # Prepare Resend parameters
        params = {
            "from": "Support Bot <onboarding@resend.dev>",
            "to": email_request.to,  
            "subject": email_request.subject,
            "html": html_content,
            "reply_to": email_request.customer_email if email_request.customer_email else None
        }
        
        # Send email
        email_response = resend.Emails.send(params)
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "email_id": email_response.get('id'),
            "to": email_request.to
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")