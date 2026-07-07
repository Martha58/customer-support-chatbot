# End-to-End Multi-Agent Customer Support AI System

## Overview

This project is an authentication-aware, multi-agent customer support AI system designed to automate customer interactions while maintaining strict data isolation and security.

The system enables customers to:

- Ask questions about their orders, deliveries, and products.
- Receive instant answers to frequently asked questions (FAQs).
- Update selected account information, such as delivery addresses.
- Submit enquiries or complaints that can be escalated to a human support team when necessary.

The AI agent combines Retrieval-Augmented Generation (RAG), business-specific tools, and authenticated database access to provide accurate, personalized responses without exposing direct database access to the language model.

---

# System Architecture

The application follows a modular architecture consisting of four primary components.

```text
                Client
                   │
                   ▼
             FastAPI Backend
                   │
     ┌─────────────┴─────────────┐
     │                           │
Authentication              AI Agent
(User Context)         (LangChain + LangGraph)
     │                           │
     │                    Tool Calling
     │                           │
     ├──────────────┬────────────┤
     ▼              ▼            ▼
 PostgreSQL     Pinecone      Email Service
Business Data   FAQ Vector DB   (Resend)
```

The FastAPI backend authenticates every user request before forwarding it to the AI agent. The authenticated user context is injected into the agent, ensuring that all tool executions operate only on data belonging to the logged-in customer.

---

# Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend API | FastAPI | Authentication, API endpoints, and request handling |
| LLM Framework | LangChain | Agent orchestration and tool calling |
| Agent Memory | LangGraph | Conversation state management using checkpointing |
| Checkpointer | InMemorySaver | Stores conversation state during runtime |
| Database | PostgreSQL | Stores business and customer data |
| Vector Database | Pinecone | Stores embeddings for business FAQs |
| Embedding Model | LangChain Embeddings | Converts FAQ documents into vector representations |
| Email Service | Resend | Sends support emails and escalated enquiries |

---

# Project Structure

## `models/`

Contains the application's database and vector database components.

### `vector_db.py`

Responsible for populating the Pinecone vector database.

**Responsibilities:**

- Loading FAQ documents
- Splitting documents into chunks
- Generating embeddings
- Uploading embeddings into Pinecone

This enables semantic search over business knowledge using Retrieval-Augmented Generation (RAG).

---

## `chatbot.py`

This file contains the core AI agent implementation.

**Responsibilities:**

- Initializing the language model
- Configuring LangChain tools
- Connecting to PostgreSQL
- Retrieving business knowledge from Pinecone
- Managing agent workflows
- Executing customer-specific actions

### Available Tools

The agent interacts with business data exclusively through predefined tools.

Current tools include:

- `get_customer_order_details`
- `get_delivery_details`
- `get_product_details`
- `update_delivery_address`
- `retrieve_faq`
- `send_email`
- `log_enquiry`

Rather than allowing the LLM to generate arbitrary SQL queries, all database interactions are encapsulated within controlled tools. This approach improves security, enforces business rules, and prevents unauthorized database access.

---

## `fastapi_app/`

Contains the backend application.

**Responsibilities:**

- User authentication
- Customer registration
- Login endpoints
- Chat API
- Email integration
- Session management
- API routing

The FastAPI layer serves as the gateway between client applications and the AI agent.

---

# Authentication and Security

Security is a core design principle of this system.

Every AI interaction is tied to an authenticated user session. Before the agent executes any tool or retrieves customer-specific information, the backend validates the user's identity and injects the authenticated customer context into the agent.

This design ensures:

- Customers can access only their own information.
- Customer data cannot be leaked across conversations.
- The LLM never receives unrestricted database access.
- All database operations are executed through controlled backend tools.

By separating authentication from agent reasoning, the system maintains strong data isolation while allowing the AI to deliver personalized responses.

---

# Retrieval-Augmented Generation (RAG)

Business FAQs are stored in Pinecone as vector embeddings.

When a customer asks a general business question, the agent:

1. Converts the user's query into an embedding.
2. Performs semantic similarity search in Pinecone.
3. Retrieves the most relevant FAQ entries.
4. Uses the retrieved context to generate an accurate response.

This allows the assistant to answer business-specific questions without relying solely on the language model's pre-trained knowledge.

---

# Conversation Memory

The application uses LangGraph's checkpointing mechanism with `InMemorySaver` to maintain conversational context during runtime.

Conversation memory enables the agent to:

- Understand follow-up questions.
- Maintain conversational continuity.
- Preserve context across multiple tool calls within a session.

Future iterations may replace `InMemorySaver` with a persistent checkpointer (such as PostgreSQL or Redis) to support long-term conversation history and horizontal scalability.

---

# Running the Application

## Clone the repository

```bash
git clone <repository-url>
```

## Create a virtual environment

```bash
python -m venv venv
```

## Activate the environment

### Windows

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
source venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Start the FastAPI server

```bash
uvicorn fastapi_app.main:app --reload
```

## Access the API documentation

```
http://localhost:8000/docs
```

---

# Future Enhancements

Planned improvements include:

- Expanding the agent's toolset to support additional customer service workflows.
- Replacing in-memory checkpointing with persistent conversation memory.
- Building an interactive web frontend for customer interactions.
- Integrating with existing business or e-commerce platforms.
- Supporting multiple business domains through configurable knowledge bases.
- Adding observability, monitoring, and analytics for agent performance.
- Implementing role-based access control (RBAC) for administrative operations.
- Introducing human-in-the-loop workflows for complex enquiries and escalations.

---

# Design Principles

This system was designed with the following principles:

- **Security First** – Database access is restricted to predefined backend tools.
- **Authentication-Aware** – Every request is associated with an authenticated customer.
- **Modular Architecture** – Components are separated for maintainability and scalability.
- **Retrieval-Augmented Generation (RAG)** – Business knowledge is retrieved from Pinecone instead of relying solely on model memory.
- **Extensible Tooling** – New business capabilities can be added by implementing additional tools without modifying the overall agent architecture.
- **Production-Oriented** – The architecture is designed to evolve toward persistent memory, monitoring, scalable infrastructure, and enterprise integrations.