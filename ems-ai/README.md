# EMS AI Enhancement – Python AI Services

> AI-powered enhancement for the **Evaluator Mapping System (EMS)** using Python, LangChain, MCP, and LangGraph.

---

## Overview

This directory contains the complete Python AI layer that enhances the existing Spring Boot + Angular EMS application with three specialized AI agents that collaborate through a LangGraph orchestrator.

## Architecture

```
Outlook CSV / EML exports
         |
         v
  Email Import Service (Python)
         |
         v
  Shared Outlook DB (MySQL – same DB as EMS)
         |
         v
  Python MCP Server (10 tools)
         |
    +----+----+
    |    |    |
 Agent1 Agent2 Agent3  ? LangChain
    |    |    |
    +----+----+
         |
         v
  LangGraph Orchestrator
         |
         v
  EMS Spring Boot Backend (REST)
         |
         v
  Angular Frontend (unchanged)
```

## Three AI Agents

| Agent | File | Responsibility |
|---|---|---|
| **Agent 1** | `app/agents/agent_1_availability/` | Scans Outlook emails for OOO/leave/unavailability signals |
| **Agent 2** | `app/agents/agent_2_mapper/` | AI-powered workload-balanced evaluator-to-candidate mapping |
| **Agent 3** | `app/agents/agent_3_validator/` | Pre-confirmation rule audit against all 5 EMS business rules |

## Prerequisites

- Python 3.11+
- MySQL 8.x (same instance as EMS backend)
- EMS Spring Boot backend running on port 8080

## Setup

### 1. Create virtual environment

```bash
cd ems-ai
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
# - DB_HOST, DB_USERNAME, DB_PASSWORD
# - LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
# - EMS_API_BASE_URL, EMS_API_JWT_TOKEN
```

### 4. Apply database migration

```bash
# Run against your MySQL instance
mysql -u root -p evaluator_mapping_db < migrations/create_outlook_tables.sql
```

### 5. Import sample email data (optional)

```bash
python -c "
import asyncio
from app.email_import.import_service import EmailImportService
asyncio.run(EmailImportService().import_from_directory('./data/imports'))
"
```

## Running the Services

### Start the AI Workflow API

```bash
python main.py
# API available at: http://localhost:8001
# Swagger UI:       http://localhost:8001/docs
```

### Start the MCP Server

```bash
python -m app.mcp_server.server
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ai/workflow/start` | Start a new AI mapping workflow |
| POST | `/api/ai/workflow/approve` | Submit human approval/rejection |
| GET | `/api/ai/workflow/{id}/status` | Get workflow status |
| POST | `/api/ai/email/import` | Import emails from directory |
| GET | `/api/ai/health` | Health check |

### Start workflow example

```bash
curl -X POST http://localhost:8001/api/ai/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "cohort_id": 1,
    "round_type": "INTERIM",
    "attempt": 1,
    "interview_from": "2024-12-01",
    "interview_to": "2024-12-05"
  }'
```

### Approve workflow example

```bash
curl -X POST "http://localhost:8001/api/ai/workflow/approve" \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "<uuid>", "approved": true}'
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# End-to-end tests
pytest tests/end_to_end/ -v
```

## Docker Deployment

```bash
cp .env.example .env
# Fill in .env

docker-compose up --build
```

Services:
- **ems-ai**: Workflow API ? `http://localhost:8001`
- **ems-mcp**: MCP Server ? `http://localhost:8002`
- **mysql**: MySQL 8 ? `localhost:3306`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `evaluator_mapping_db` | Database name |
| `DB_USERNAME` | `root` | MySQL username |
| `DB_PASSWORD` | _(empty)_ | MySQL password |
| `LLM_PROVIDER` | `openai` | LLM provider: `openai`, `google`, `anthropic` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_API_KEY` | _(required)_ | API key for the LLM provider |
| `LLM_TEMPERATURE` | `0.0` | LLM temperature |
| `EMS_API_BASE_URL` | `http://localhost:8080` | EMS Spring Boot backend URL |
| `EMS_API_JWT_TOKEN` | _(required)_ | JWT token to call EMS APIs |
| `API_PORT` | `8001` | Workflow API port |
| `MCP_PORT` | `8002` | MCP server port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Integration with EMS Backend

The Spring Boot backend has two new components added (non-breaking):

- `AIWorkflowController.java` ? routes `/api/ai/**` to the Python service
- `AIWorkflowService.java` ? HTTP client calls to `AI_SERVICE_URL`

The Angular frontend gains an **?? AI Auto-Map** button on the mapping page that uses `AIWorkflowService` to trigger the Python workflow.

## Future: Microsoft Graph API Integration

To enable live Outlook synchronisation when Graph API access is available:
1. Add `MS_GRAPH_CLIENT_ID`, `MS_GRAPH_CLIENT_SECRET`, `MS_GRAPH_TENANT_ID` to `.env`
2. Implement `app/integrations/graph_sync.py` using the `msgraph-sdk` package
3. The import service already supports `data_source = "GRAPH_SYNC"` and incremental imports
4. All three agents will automatically use the richer live data with zero code changes

## Project Structure

```
ems-ai/
+-- app/
¦   +-- config/settings.py          # Pydantic env-driven config
¦   +-- utils/logging.py            # Centralized logging
¦   +-- database/
¦   ¦   +-- connection.py           # SQLAlchemy async engine
¦   ¦   +-- models/                 # 5 ORM models
¦   ¦   +-- repositories/          # EmailRepository + AgentRepository
¦   +-- email_import/
¦   ¦   +-- parsers/csv_parser.py   # CSV email import
¦   ¦   +-- parsers/eml_parser.py   # EML file import
¦   ¦   +-- import_service.py       # Import orchestrator
¦   +-- mcp_server/
¦   ¦   +-- server.py               # FastMCP server (10 tools)
¦   ¦   +-- tools/                  # email, attachment, ems tools
¦   +-- agents/
¦   ¦   +-- llm_factory.py          # Provider-agnostic LLM factory
¦   ¦   +-- base_agent.py           # BaseEMSAgent
¦   ¦   +-- agent_1_availability/   # Evaluator Availability Agent
¦   ¦   +-- agent_2_mapper/         # Evaluator Mapping Agent
¦   ¦   +-- agent_3_validator/      # Mapping Validation Agent
¦   +-- orchestration/
¦       +-- state.py                # EMSWorkflowState TypedDict
¦       +-- nodes.py                # 7 node functions
¦       +-- routing.py              # Conditional routing
¦       +-- graph.py                # LangGraph StateGraph
¦       +-- workflow_api.py         # FastAPI HTTP interface
+-- migrations/
¦   +-- create_outlook_tables.sql   # 5 new MySQL tables
+-- data/imports/
¦   +-- sample_emails.csv           # 10 sample Outlook emails
+-- tests/
¦   +-- unit/test_database.py
¦   +-- integration/test_mcp_tools.py
¦   +-- end_to_end/test_e2e_workflow.py
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
+-- .env.example
+-- pytest.ini
+-- main.py
```
