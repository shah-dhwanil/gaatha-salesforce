"""
Agentic sales assistant module.

Provides an orchestrator-based system using LangGraph that classifies user
intent (query vs. action), routes to specialised sub-agents, manages
conversation memory in DynamoDB, and uses explicit HTTP-based tools to call
the REST API for all CRUD operations.
"""
