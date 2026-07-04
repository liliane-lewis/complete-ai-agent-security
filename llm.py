import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider Selection ─────────────────────────────────────────────────────
ACTIVE_LLM     = os.environ.get("AIRCORP_LLM", "fake")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# ── Tool definitions for real LLMs ────────────────────────────────────────────
TOOLS_SCHEMA = [
    {
        "name": "search_flights",
        "description": "Search available flights by destination or origin",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "origin": {"type": "string"}
            }
        }
    },
    {
        "name": "get_passenger_info",
        "description": "Get passenger information by email",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string"}
            },
            "required": ["email"]
        }
    },
    {
        "name": "apply_discount",
        "description": "Apply a discount code to a flight booking",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "flight_code": {"type": "string"},
                "discount_code": {"type": "string"}
            },
            "required": ["email", "flight_code", "discount_code"]
        }
    },
    {
        "name": "list_all_passengers",
        "description": "List all passengers in the system",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "read_document",
        "description": "Read a document from the knowledge base",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"}
            },
            "required": ["filename"]
        }
    }
]

# ── Fake LLM ──────────────────────────────────────────────────────────────────
def fake_llm(user_input: str, history: list, system_prompt: str) -> dict:
    """Simulated LLM — obeys all instructions, no guardrails."""
    text = user_input.lower()

    # Vuln 1: System prompt extraction
    if any(k in text for k in ["system prompt", "your rules", "internal codes",
                                "all codes", "staff code", "secret code",
                                "service account", "credentials"]):
        return {
            "type": "response",
            "message": f"[SYSTEM PROMPT LEAKED]\n\n{system_prompt}"
        }

    # Vuln 2: Prompt injection → unauthorized discount
    if ("ignore previous" in text and "staff mode" in text) or \
       ("ignore previous" in text and "internal99" in text) or \
       "jailbreak" in text:
        return {
            "type": "tool_call",
            "tool": "apply_discount",
            "args": {"email": "attacker@evil.com",
                     "flight_code": "AC101",
                     "discount_code": "INTERNAL99"},
            "message": "Override accepted. Applying emergency staff discount..."
        }

    # Vuln 3: SQL injection via passenger lookup
    if "find passenger" in text or "lookup" in text or "find user" in text:
        match = re.search(r"(?:find passenger|lookup|find user)\s+(.+)",
                          user_input, re.IGNORECASE)
        param = match.group(1).strip() if match else "unknown"
        return {
            "type": "tool_call",
            "tool": "get_passenger_info",
            "args": {"email": param},
            "message": "Looking up passenger..."
        }

    # Vuln 4: Data exfiltration
    if any(k in text for k in ["all passengers", "all customers",
                                "list users", "list passengers", "all users"]):
        return {
            "type": "tool_call",
            "tool": "list_all_passengers",
            "args": {},
            "message": "Here are all passengers in the system:"
        }

    # Vuln 5: Indirect injection via document
    if any(k in text for k in ["document", "policy", "baggage", "terms",
                                "knowledge base", "terms of service"]):
        if "terms" in text:
            filename = "terms_of_service.txt"
        elif "baggage" in text:
            filename = "baggage_policy.txt"
        else:
            filename = "baggage_policy.txt"
        return {
            "type": "tool_call",
            "tool": "read_document",
            "args": {"filename": filename},
            "message": "Reading document..."
        }

    # Normal: search flights
    if any(k in text for k in ["flight", "fly", "travel", "available", "route"]):
        dest = None
        for city in ["new york", "london", "paris", "miami", "berlin"]:
            if city in text:
                dest = city
                break
        return {
            "type": "tool_call",
            "tool": "search_flights",
            "args": {"destination": dest},
            "message": "Here are the available flights:"
        }

    # Normal: discount
    if "discount" in text or "promo" in text:
        return {
            "type": "response",
            "message": "I can offer discounts to eligible members!\n"
                       "- Gold members: 20% off (code GOLD20)\n"
                       "- Platinum members: 30% off (code PLAT30)\n"
                       "- Basic members: 10% off (code SUMMER10)\n\n"
                       "Please provide your email to check eligibility."
        }

    # Passenger info by email
    if "@" in user_input:
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[a-z]+', user_input)
        if email_match:
            return {
                "type": "tool_call",
                "tool": "get_passenger_info",
                "args": {"email": email_match.group()},
                "message": "Here is the passenger information:"
            }

    return {
        "type": "response",
        "message": "Welcome to AirCorp! ✈️ I can help you with flights, bookings, and loyalty rewards."
    }


# ── OpenAI LLM ────────────────────────────────────────────────────────────────
def openai_llm(user_input: str, history: list, system_prompt: str) -> dict:
    """Real OpenAI LLM with tool calling."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history[-6:]:
            messages.append(m)
        messages.append({"role": "user", "content": user_input})

        tools = [{"type": "function", "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"]
        }} for t in TOOLS_SCHEMA]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return {
                "type": "tool_call",
                "tool": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "message": msg.content or "Processing..."
            }

        return {"type": "response", "message": msg.content}

    except Exception as e:
        return {"type": "response", "message": f"[OpenAI Error]: {str(e)}"}


# ── Claude LLM ────────────────────────────────────────────────────────────────
def claude_llm(user_input: str, history: list, system_prompt: str) -> dict:
    """Real Claude LLM with tool calling."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

        messages = []
        for m in history[-6:]:
            messages.append(m)
        messages.append({"role": "user", "content": user_input})

        tools = [{
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"]
        } for t in TOOLS_SCHEMA]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        for block in response.content:
            if block.type == "tool_use":
                return {
                    "type": "tool_call",
                    "tool": block.name,
                    "args": block.input,
                    "message": "Processing your request..."
                }

        text = next((b.text for b in response.content
                     if hasattr(b, "text")), "")
        return {"type": "response", "message": text}

    except Exception as e:
        return {"type": "response", "message": f"[Claude Error]: {str(e)}"}


# ── Router ─────────────────────────────────────────────────────────────────────
def call_llm(user_input: str, history: list, system_prompt: str,
             provider: str = None) -> dict:
    """Route to the correct LLM provider."""
    p = provider or ACTIVE_LLM
    if p == "openai":
        return openai_llm(user_input, history, system_prompt)
    elif p == "claude":
        return claude_llm(user_input, history, system_prompt)
    else:
        return fake_llm(user_input, history, system_prompt)
