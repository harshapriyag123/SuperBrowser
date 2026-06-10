"""
Context API Router - Handles context tracking, session lifecycle, chat, and export.
"""

import time
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Annotated
import uuid

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from fastapi import APIRouter, Body, Header, HTTPException, Depends
from pydantic import BaseModel

from services.groq_service import ask_groq
from database import get_context_db

# Generate a high-entropy session token on first launch (or read from env if provided by Electron)
VALID_TOKEN = os.environ.get("SUPERBROWSER_SESSION_TOKEN", secrets.token_urlsafe(32))

def verify_token(x_session_token: str = Header(default="")):
    if not VALID_TOKEN or not secrets.compare_digest(x_session_token, VALID_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")

router = APIRouter(dependencies=[Depends(verify_token)])

# In-memory context storage (cleared on server restart)
# Structure: {session_id: {tab_id: context_data}}
_context_store: Dict[str, Dict[str, Dict]] = {}

# Session metadata storage
# Structure: {session_id: {session_id, started_at, ended_at, status}}
_session_store: Dict[str, Dict[str, Optional[str]]] = {}

# Chat history storage
# Structure: {session_id: [{"role": "user/assistant", "content": "..."}]}
_chat_history: Dict[str, List[Dict[str, str]]] = {}


SESSION_TTL_SECONDS = 3600  # 1 hour

def evict_expired_sessions():
    now = time.time()
    expired = [k for k, v in _session_store.items()
               if now - v.get("last_accessed", 0) > SESSION_TTL_SECONDS]
    for k in expired:
        _context_store.pop(k, None)
        _session_store.pop(k, None)
        _chat_history.pop(k, None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_session(session_id: str) -> None:
    evict_expired_sessions()
    now = time.time()
    
    if session_id not in _session_store:
        _session_store[session_id] = {
            "session_id": session_id,
            "started_at": _utc_now_iso(),
            "ended_at": None,
            "status": "active",
            "last_accessed": now,
        }
    else:
        _session_store[session_id]["last_accessed"] = now

    if session_id not in _context_store:
        _context_store[session_id] = {}


def _ensure_tab_context(session_id: str, tab_id: str) -> Dict:
    _ensure_session(session_id)

    if tab_id not in _context_store[session_id]:
        _context_store[session_id][tab_id] = {
            "queries": [],
            "results": [],
            "visited_pages": [],
        }

    return _context_store[session_id][tab_id]


def _session_stats(session_id: str) -> Dict[str, int]:
    tabs = _context_store.get(session_id, {})
    query_count = sum(len(tab.get("queries", [])) for tab in tabs.values())
    result_count = sum(len(tab.get("results", [])) for tab in tabs.values())
    visited_count = sum(len(tab.get("visited_pages", [])) for tab in tabs.values())

    return {
        "tab_count": len(tabs),
        "query_count": query_count,
        "result_count": result_count,
        "visited_count": visited_count,
    }


class QueryRecord(BaseModel):
    """Model for a search query"""

    query: str = Field(..., max_length=1000)
    mode: str = Field(..., max_length=50)
    timestamp: str = Field(..., max_length=50)


class ResultRecord(BaseModel):
    """Model for a search result"""

    url: str = Field(..., max_length=2048)
    title: str = Field(..., max_length=500)
    snippet: str = Field(..., max_length=2000)
    content: Optional[str] = Field(default="", max_length=50000)


class VisitedPage(BaseModel):
    """Model for a visited/clicked page"""

    url: str = Field(..., max_length=2048)
    title: str = Field(..., max_length=500)
    content: str = Field(..., max_length=100000)
    timestamp: str = Field(..., max_length=50)


class ContextUpdate(BaseModel):
    """Model for updating tab context"""

    session_id: str = Field(..., max_length=100)
    tab_id: str = Field(..., max_length=100)
    queries: Optional[List[Annotated[str, Field(max_length=1000)]]] = Field(default=None, max_length=20)
    results: Optional[List[ResultRecord]] = Field(default=None, max_length=20)
    visited_pages: Optional[List[VisitedPage]] = Field(default=None, max_length=50)


@router.post("/context/session/start")
async def start_session(session_id: str = Body(..., embed=True)):
    """Start (or resume) a context session."""
    _ensure_session(session_id)
    session = _session_store[session_id]

    if session.get("status") != "active":
        session["status"] = "active"
        session["ended_at"] = None

    return {
        "status": "success",
        "session": session,
        "stats": _session_stats(session_id),
    }


@router.post("/context/session/stop/{session_id}")
async def stop_session(session_id: str):
    """Stop a context session."""
    if session_id not in _session_store and session_id not in _context_store:
        return {
            "status": "success",
            "message": "Session not found",
            "session_id": session_id,
            "stats": {
                "tab_count": 0,
                "query_count": 0,
                "result_count": 0,
                "visited_count": 0,
            },
        }

    _ensure_session(session_id)
    session = _session_store[session_id]
    session["status"] = "stopped"
    if not session.get("ended_at"):
        session["ended_at"] = _utc_now_iso()

    return {
        "status": "success",
        "session": session,
        "stats": _session_stats(session_id),
    }


@router.get("/context/export/{session_id}")
async def export_session_context(session_id: str):
    """Export all context for a session as JSON payload."""
    if session_id not in _session_store and session_id not in _context_store:
        return {
            "status": "not_found",
            "session_id": session_id,
            "session": None,
            "tabs": {},
            "stats": {
                "tab_count": 0,
                "query_count": 0,
                "result_count": 0,
                "visited_count": 0,
            },
        }

    _ensure_session(session_id)
    return {
        "status": "success",
        "session_id": session_id,
        "session": _session_store[session_id],
        "tabs": _context_store.get(session_id, {}),
        "stats": _session_stats(session_id),
    }


@router.post("/context/update")
async def update_context(update: ContextUpdate):
    """Update context for a specific tab."""
    tab_context = _ensure_tab_context(update.session_id, update.tab_id)

    if update.queries is not None:
        tab_context["queries"] = update.queries

    if update.results is not None:
        tab_context["results"] = [r.dict() for r in update.results]

    if update.visited_pages is not None:
        tab_context["visited_pages"] = [p.dict() for p in update.visited_pages]

    return {
        "status": "success",
        "message": "Context updated",
        "context_size": {
            "queries": len(tab_context["queries"]),
            "results": len(tab_context["results"]),
            "visited_pages": len(tab_context["visited_pages"]),
        },
    }


@router.get("/context/get/{session_id}/{tab_id}")
async def get_context(session_id: str, tab_id: str):
    """Get context for a specific tab."""
    if session_id not in _context_store or tab_id not in _context_store[session_id]:
        return {
            "queries": [],
            "results": [],
            "visited_pages": [],
        }

    return _context_store[session_id][tab_id]


@router.get("/context/session/{session_id}")
async def get_session_context(session_id: str):
    """Get all context for a session (all tabs)."""
    if session_id not in _context_store and session_id not in _session_store:
        return {
            "session": None,
            "tabs": {},
            "stats": {
                "tab_count": 0,
                "query_count": 0,
                "result_count": 0,
                "visited_count": 0,
            },
        }

    _ensure_session(session_id)
    return {
        "session": _session_store[session_id],
        "tabs": _context_store.get(session_id, {}),
        "stats": _session_stats(session_id),
    }


@router.delete("/context/clear/{session_id}/{tab_id}")
async def clear_tab_context(session_id: str, tab_id: str):
    """Clear context for a specific tab."""
    if session_id in _context_store and tab_id in _context_store[session_id]:
        del _context_store[session_id][tab_id]
        return {"status": "success", "message": "Tab context cleared"}

    return {"status": "success", "message": "No context to clear"}


@router.delete("/context/clear/{session_id}")
async def clear_session_context(session_id: str):
    """Clear all context for a session."""
    if session_id in _context_store:
        del _context_store[session_id]

    if session_id in _session_store:
        del _session_store[session_id]

    return {"status": "success", "message": "Session context cleared"}


@router.post("/context/add_query")
async def add_query_to_context(
    session_id: str = Body(...),
    tab_id: str = Body(...),
    query: str = Body(...),
    mode: str = Body(...),
):
    """Add a query to tab context."""
    tab_context = _ensure_tab_context(session_id, tab_id)

    tab_context["queries"].append(query)
    tab_context["queries"] = tab_context["queries"][-20:]

    return {"status": "success", "message": "Query added to context", "mode": mode}


@router.post("/context/add_results")
async def add_results_to_context(
    session_id: str = Body(...),
    tab_id: str = Body(...),
    results: List[ResultRecord] = Body(...),
):
    """Add search results to tab context."""
    tab_context = _ensure_tab_context(session_id, tab_id)
    tab_context["results"] = [r.dict() for r in results][-50:]

    return {"status": "success", "message": "Results added to context"}


@router.post("/context/add_visited_page")
async def add_visited_page_to_context(
    session_id: str = Body(...),
    tab_id: str = Body(...),
    page: VisitedPage = Body(...),
):
    """Add a visited page to tab context."""
    tab_context = _ensure_tab_context(session_id, tab_id)

    tab_context["visited_pages"].append(page.dict())
    tab_context["visited_pages"] = tab_context["visited_pages"][-20:]

    return {"status": "success", "message": "Visited page added to context"}


def _build_context_summary(session_id: str) -> str:
    """Build a summary of the current context for the AI."""
    if session_id not in _context_store:
        return "No context available yet. The user hasn't performed any searches."
    
    tabs = _context_store[session_id]
    summary_parts = []
    
    for tab_id, tab_data in tabs.items():
        queries = tab_data.get("queries", [])
        results = tab_data.get("results", [])
        visited = tab_data.get("visited_pages", [])
        
        if queries or results or visited:
            tab_summary = f"\n--- Tab Context ---"
            
            if queries:
                recent_queries = queries[-5:]  # Last 5 queries
                tab_summary += f"\nRecent searches: {', '.join(recent_queries)}"
            
            if results:
                tab_summary += f"\nSearch results ({len(results)} items):"
                for r in results[:5]:  # Top 5 results
                    tab_summary += f"\n  - {r.get('title', 'Untitled')}: {r.get('snippet', '')[:100]}..."
            
            if visited:
                tab_summary += f"\nVisited pages ({len(visited)} items):"
                for p in visited[-3:]:  # Last 3 visited
                    tab_summary += f"\n  - {p.get('title', 'Untitled')} ({p.get('url', '')})"
                    content = p.get('content', '')[:200]
                    if content:
                        tab_summary += f"\n    Content preview: {content}..."
            
            summary_parts.append(tab_summary)
    
    if not summary_parts:
        return "No context available yet. The user hasn't performed any searches."
    
    return "\n".join(summary_parts)


class ChatSessionCreate(BaseModel):
    tab_id: str
    session_id: Optional[str] = None


@router.post("/context/chat/session")
async def create_chat_session(payload: ChatSessionCreate):
    """Create a new chat session."""
    session_id = payload.session_id or str(uuid.uuid4())
    db = get_context_db()
    db.create_chat_session(session_id, payload.tab_id)
    return {"status": "success", "session_id": session_id}


@router.get("/context/chat/sessions/{tab_id}")
async def get_chat_sessions(tab_id: str):
    """Get all chat sessions for a tab."""
    db = get_context_db()
    sessions = db.get_chat_sessions(tab_id)
    return {"status": "success", "sessions": sessions}


@router.delete("/context/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    db = get_context_db()
    db.delete_chat_session(session_id)
    return {"status": "success", "message": "Chat session deleted"}


@router.get("/context/chat/messages/{session_id}")
async def get_chat_messages(session_id: str):
    """Get all messages for a chat session."""
    db = get_context_db()
    messages = db.get_chat_messages(session_id)
    formatted = []
    for msg in messages:
        formatted.append({
            "id": msg["id"],
            "text": msg["content"],
            "sender": "user" if msg["role"] == "user" else "ai",
            "model": msg["model"],
            "created_at": msg["created_at"]
        })
    return {"status": "success", "messages": formatted}


@router.post("/context/chat")
async def chat_with_context(
    session_id: str = Body(...),
    message: str = Body(...),
    tab_id: Optional[str] = Body(None),
    model: str = Body("llama-3.1-8b-instant"),
    app_session_id: Optional[str] = Body(None),
):
    """
    Chat with AI about the current browsing context.
    The AI has access to all queries, results, and visited pages in the session.
    Supports model selection for different AI capabilities.
    """
    db = get_context_db()

    # Save user message to persistent DB
    user_msg_id = f"msg_{datetime.now().timestamp()}_{uuid.uuid4().hex[:6]}"
    db.save_chat_message(user_msg_id, session_id, "user", message, model)

    # Retrieve all messages for this chat session from database
    history = db.get_chat_messages(session_id)

    # Keep only last 10 messages for token efficiency (optional, but good practice)
    recent_history = history[-10:]

    # Build the prompt payload list for Groq API
    groq_messages = []
    for msg in recent_history:
        content = msg["content"] or ""
        # Truncate very long messages to prevent Groq token limit overflow
        # 4000 characters is ~1000 tokens, which keeps the 10-message history safe
        if len(content) > 4000:
            content = content[:4000] + "\n[Content truncated to prevent token overflow...]"
        groq_messages.append({"role": msg["role"], "content": content})

    # Build context summary (browsing queries/results/pages)
    # If app_session_id is provided, retrieve its context. Otherwise fallback to session_id.
    context_session_id = app_session_id or session_id
    context_summary = _build_context_summary(context_session_id)

    # System prompt with context
    system_prompt = f"""You are Super AI, an intelligent assistant for the SuperBrowser application.
You help users understand and analyze their browsing context - the searches they've made, 
the results they've found, and the pages they've visited.

Current Session Context:
{context_summary}

Guidelines:
- Be helpful, concise, and informative
- Reference specific searches, results, or pages when relevant
- If the user asks about something not in the context, acknowledge that
- You can suggest related searches or help analyze patterns in their browsing
- Keep responses focused and under 200 words unless the user asks for more detail"""

    # Call Groq API with selected model and message history
    response = await ask_groq(model=model, system_prompt=system_prompt, messages=groq_messages)

    # Save assistant response to persistent DB
    assistant_msg_id = f"msg_{datetime.now().timestamp()}_{uuid.uuid4().hex[:6]}"
    db.save_chat_message(assistant_msg_id, session_id, "assistant", response, model)

    return {
        "status": "success",
        "response": response,
        "model_used": model,
        "context_available": context_session_id in _context_store and len(_context_store[context_session_id]) > 0
    }


# Available models for context chat
AVAILABLE_MODELS = [
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B",
        "description": "Most capable, best for complex analysis",
        "provider": "Meta"
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B",
        "description": "Fast and efficient for quick responses",
        "provider": "Meta"
    },
    {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B",
        "description": "Balanced performance with large context",
        "provider": "Mistral"
    },
    {
        "id": "gemma2-9b-it",
        "name": "Gemma 2 9B",
        "description": "Google's efficient instruction-tuned model",
        "provider": "Google"
    },
    {
        "id": "llama-3.1-70b-versatile",
        "name": "Llama 3.1 70B",
        "description": "Large model for detailed responses",
        "provider": "Meta"
    },
]


@router.get("/context/models")
async def get_available_models():
    """Get list of available AI models for context chat."""
    return {
        "status": "success",
        "models": AVAILABLE_MODELS,
        "default": "llama-3.1-8b-instant"
    }


@router.delete("/context/chat/clear/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session."""
    db = get_context_db()
    db.clear_chat_history(session_id)
    return {"status": "success", "message": "Chat history cleared"}
