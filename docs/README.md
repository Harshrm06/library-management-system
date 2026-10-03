# Documentation

Reference documents for the Library Management System.

| Document | Status | Description |
| --- | --- | --- |
| `API.md` | Planned | Endpoint reference for the FastAPI backend (Swagger: http://localhost:8000/docs) |
| `DATABASE.md` | Planned | Schema, relationships, and migration notes |
| `TESTING.md` | Planned | Manual and Postman test procedures |

Source of truth for requirements is the project PRD (`Library_Management_System_PRD.md` in the repository root).

## Conventions

- Keep request/response examples in sync with the Pydantic schemas in `backend/app/schemas`.
- Document every environment variable added to `backend/.env.example` and `frontend/.env.example` here.
- Use Markdown only; keep one document per topic.