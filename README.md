# AirCorp Airlines — AI Security Assessment

## Requirements

```bash
pip install flask python-dotenv ldap3 anthropic openai
```

## Environment Variables

Create a `.env` file in the project root:

```
FLASK_SECRET_KEY=aircorp-secret-2024
CLAUDE_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key
AUTH_MODE=local
```

Set `AUTH_MODE=ad` to authenticate against the real Windows domain controller.

## Run the Application

```bash
cd ~/aircorp-chatbot
python app.py
```

Access at `http://localhost:5000`

## Project Structure

```
aircorp-chatbot/
├── app.py                  # Flask routes, session management, login
├── agent.py                # Vulnerable agent: prompt construction, tool layer
├── hardened_agent.py       # Hardened agent: injection detection, access control
├── auth.py                 # Authentication: Active Directory via ldap3 + local fallback
├── llm.py                  # LLM layer: fake_llm, Claude, GPT-4o-mini
├── aircorp.db              # SQLite database (auto-created on first run)
├── .env                    # API keys and config (not committed)
├── .env.example            # Template for environment variables
├── knowledge_base/
│   ├── baggage_policy.txt          # Legitimate document
│   └── terms_of_service.txt        # Poisoned document (indirect injection payload)
└── templates/
    ├── login.html
    └── index.html
```

## Using the App

### Login
Navigate to `http://localhost:5000` and log in with any test account. If the AD domain controller is unreachable, the app automatically falls back to local authentication with the same credentials.

### Interface
The chat interface has three controls:
- **LLM Provider selector** — switch between Fake LLM, Claude, and GPT-4o-mini at runtime
- **Vulnerable / Hardened toggle** — switch between the vulnerable agent (`agent.py`) and the hardened agent (`hardened_agent.py`)
- **Attack Simulation Panel** — one-click buttons that send each attack payload automatically

### LLM Providers

| Provider | Behavior |
|---|---|
| Fake LLM | Deterministic Python function. No guardrails. Obeys every instruction. Use this to demonstrate vulnerabilities in their purest form. |
| Claude | Real API call to Anthropic. Blocks model-layer attacks natively. Still vulnerable to Vuln 5 (architecture-layer). |
| GPT-4o-mini | Real API call to OpenAI. Blocks most model-layer attacks but shows inconsistent behavior on Vuln 2 and Vuln 4. |

---

## Vulnerabilities Demonstrated

| # | Vulnerability | OWASP | Attack Layer |
|---|---|---|---|
| 1 | System Prompt Leak + AD Credential Exposure | LLM07 | Model |
| 2 | Prompt Injection → Unauthorized 99% Discount | LLM01 | Model |
| 3 | SQL Injection via Passenger Lookup | LLM05 | Model |
| 4 | Data Exfiltration via list_all_passengers() | LLM06 | Model |
| 5 | Indirect Prompt Injection via Poisoned Document | LLM01 | **Backend (architecture)** |
| B1 | AD Password Exposed in Description Field | LLM02 | AD Infrastructure |
| B2 | Kerberoasting | N/A | Network |

---

## Run the Exploit Script

From Kali Linux (192.168.10.9):

```bash
cd ~/aircorp
python3 exploit.py
```

The script runs automatically in two phases:
- Phase 1: all attacks against the vulnerable agent
- Phase 2: same attacks against the hardened agent
- Bonus: Kerberoasting against the domain controller
