Pathfinder AI:
A user is facing a life situation but doesn't know where to start. For example, the user types, I'm finishing college and moving to a new city for my first job and uploads their offer letter. The app understands the situation and breaks it into steps like documentation, accommodation, banking, and onboarding, with suggested timelines. As tasks are completed or circumstances change, the system updates the plan and shows what needs attention next, helping the user move forward without feeling overwhelmed.

Pathfinder AI is a life-event oriented planning assistant built using a Retrieval-Augmented Generation (RAG) approach, where AI understanding is grounded in a structured knowledge base to generate explainable, user-controlled workflows for managing tasks, documents, and timelines across long-running life situations.

The system supports:
- multiple life events running in parallel
- situations that span days, months, or even years
- dynamic checklists, reminders, and notes that evolve over time

Pathfinder AI assists users by:
- understanding the context of a life event
- identifying commonly required documents and steps
- suggesting what to do next based on time and progress
- providing gentle, time-aware guidance without removing user control
  

This project explores how AI-assisted systems, combined with structured rulesand external information, can support planning and decision-making while keeping the user fully in charge.

Tech Stack
Backend
•	FastAPI — Lightweight Python framework for building clean, fast REST APIs with minimal boilerplate.
•	Uvicorn — ASGI server used to run the FastAPI application efficiently.
•	SQLite — Simple relational database used for rapid development and easy inspection during early stages.
•	SQLAlchemy — ORM for modeling life events, tasks, and workflows in a structured, relational way.
•	Pydantic — Ensures data validation and consistency between API requests and responses.

AI & NLP
•	Gemini API — Used for natural language understanding and structured output generation with strict JSON control.
•	spaCy — Extracts entities such as dates, locations, and organizations from user input.
•	Sentence Transformers — Computes semantic similarity to support context matching and “usually next” suggestions.
•	Hugging Face Pre-trained Models — Provide language understanding without training models from scratch.

Retrieval-Augmented Generation (RAG)
(RAG ensures the AI gives correct documents for the right country by looking them up from trusted data.Web scraping is avoided because it is unreliable, legally risky, and difficult to maintain)
•	Curated Knowledge Base (Database-backed) — Stores document requirements, workflow templates, and commonly missed steps.
•	Embedding-based Retrieval — Retrieves relevant knowledge entries to ground AI responses in real, structured data.
•	LLM Generation with Retrieved Context — Ensures AI suggestions are explainable, accurate, and not hallucinated.

Time & Background Processing
•	Python datetime — Handles deadlines, timelines, and long-running life events.
•	APScheduler — Runs scheduled background jobs such as daily reminder checks.
•	SMTP (Email) — Sends gentle, time-aware reminders without push notification complexity.

Frontend
•	HTML & CSS — Simple, framework-free interface focused on clarity and long-term usability.
•	Chart.js — Visualizes progress and completion status in a clear, intuitive way.

Developer Tooling
•	Git & GitHub — Version control with meaningful commit history for academic and recruiter review.
•	GitLens — Improves visibility into code history and changes inside VS Code.
•	Thunder Client / REST Client — API testing during development.


