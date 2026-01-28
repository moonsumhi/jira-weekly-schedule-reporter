# Jira Weekly Mailer 
## Project 구조

project/

├─ app/

│   ├─ main.py

│   ├─ core/

│   │    └─ config.py

│   ├─ models/

│   │    └─ issue.py

│   ├─ utils/

│   │    └─ time.py              # TimeProvider, TimeUtil (KST/UTC helpers)

│   ├─ jira/

│   │    ├─ jql_builder.py       # JqlBuilder (immutable, chainable)

│   │    └─ client.py            # JiraClient (REST/search/pagination)

│   ├─ services/

│   │    └─ jira_service.py      # Orchestrates Time+JQL+Client and grouping

│   └─ routers/

│        ├─ health.py

│        └─ issues.py

└─ .env

## Install

pip install fastapi uvicorn httpx pydantic-settings python-dateutil pytz

## Run

uvicorn app.main:app --host 0.0.0.0 --port 8000

## Swagger

http://localhost:8000/docs