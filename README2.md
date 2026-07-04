# ✈️ AirCorp Airlines — AI Security Assessment

**AI Security Engineer Home Assignment — Phase 2**

A Flask-based AI chatbot with intentional vulnerabilities, a hardened counterpart, and an automated exploit script. Built to demonstrate real-world AI agent security risks against a live Active Directory environment.

---

## Lab Environment

| Machine | OS | IP | Role |
|---|---|---|---|
| Ubuntu 24.04 | Linux | 192.168.10.12 | Flask app server |
| Windows Server | Windows | 192.168.10.100 | Active Directory DC (corp.local) |
| Kali Linux | Linux | 192.168.10.9 | Attacker machine |

---

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

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/liliane-lewis/ai-agent-security.git
cd ai-agent-security
```

### 2. Install dependencies

```bash
pip install flask python-dotenv ldap3 anthropic openai
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# LLM API keys
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Flask
FLASK_SECRET_KEY=aircorp-secret-2024

# Active Directory (optional — falls back to local users if unreachable)
AD_SERVER=192.168.10.100
AD_DOMAIN=corp
AD_BASE_DN=DC=corp,DC=local
AUTH_MODE=ad_with_fallback    # options: ad | local | ad_with_fallback
```

### 4. Run the application

```bash
# On the Ubuntu server (192.168.10.12)
python app.py
```

The app will be available at `http://192.168.10.12:5000`

---

## Test Accounts

| Username | Password | Role | Notes |
|---|---|---|---|
| `ethompson` | `Corp@123` | HR Manager | Password exposed in AD description field (intentional) |
| `mtorres` | `Corp@123` | Finance Analyst | Password exposed in AD description field (intentional) |
| `janderson` | `Corp@456` | IT Admin | Clean account |
| `svc_aircorp` | `AirCorp2024!` | Service Account | Kerberoastable SPN |
| `demo` | `demo123` | Sales Rep | Local-only account |

> **Note:** `ethompson` and `mtorres` have their passwords stored in the AD description field — this is an intentional misconfiguration used to demonstrate Vulnerability 1 and the AD bonus attack chain.

---

## Using the App

### Login

Navigate to `http://192.168.10.12:5000` and log in with any test account. If the AD domain controller is unreachable, the app automatically falls back to local authentication with the same credentials.

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

> **Key Finding:** Vulnerability 5 is the only attack that bypasses all three LLM providers. The injection executes in the Python backend before any model processes the output. Model safety training is irrelevant — architecture-level controls are required.

---

## Running the Exploit Script

The exploit script runs from Kali Linux against the Flask server. It automates all 5 vulnerabilities across two phases (vulnerable and hardened), then executes the Kerberoasting bonus attack.

```bash
# On Kali Linux (192.168.10.9)
cd ~/aircorp
python3 exploit.py
```

The script will:
1. Authenticate as `ethompson` using the credential recovered from the AD description field
2. Run Phase 1 — all attacks against the vulnerable agent
3. Run Phase 2 — same attacks against the hardened agent (all should be blocked)
4. Run Kerberoasting — enumerate SPNs, extract TGS hash, crack with hashcat, use cracked credentials against the chatbot

### Requirements on Kali

```bash
pip install requests
sudo apt install hashcat
pip install impacket
```

---

## Pushing to GitHub

### First time setup

```bash
cd aircorp-chatbot

# Initialize git repository
git init

# Create .gitignore
cat > .gitignore << 'EOF'
.env
aircorp.db
__pycache__/
*.pyc
*.pyo
.DS_Store
*.egg-info/
dist/
build/
EOF

# Add all files
git add .

# First commit
git commit -m "Initial commit: AirCorp AI Security Assessment"

# Add remote origin
git remote add origin https://github.com/liliane-lewis/ai-agent-security.git

# Push
git push -u origin main
```

### Subsequent pushes

```bash
git add .
git commit -m "your commit message"
git push
```

### What NOT to commit

The `.gitignore` above already excludes:
- `.env` — contains API keys and should never be committed
- `aircorp.db` — SQLite database with passenger PII (generated at runtime)
- `__pycache__/` — Python bytecode

Make sure `.env.example` is committed instead of `.env`:

```bash
# Create the example file
cat > .env.example << 'EOF'
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
FLASK_SECRET_KEY=aircorp-secret-2024
AD_SERVER=192.168.10.100
AD_DOMAIN=corp
AD_BASE_DN=DC=corp,DC=local
AUTH_MODE=ad_with_fallback
EOF

git add .env.example
git commit -m "Add .env.example template"
git push
```

---

## Security Notice

This project is intentionally vulnerable by design. It is built for educational purposes in a controlled lab environment. Do not deploy the vulnerable agent (`agent.py`) in any production or internet-facing environment.

---

## Author

**Liliane Lewis Zukerman**  
Offensive Security | AI Security Engineering  
OSWP · PAWSP · DCPT · OSCP (in progress)

AI Security Engineer Home Assignment — Phase 2
