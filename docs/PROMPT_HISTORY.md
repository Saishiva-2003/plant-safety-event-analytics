# Prompt History

This project was built in one hackathon session (14 Nov 2026, ~13:56 → ~18:15 IST) with an AI assistant
(Claude) acting as pair programmer. The developer drove every step, created and ran every file locally
in VS Code, and tested each file before moving on. Prompts are listed in order, lightly condensed and
grammar-corrected; the outcome column says what was produced or decided.

| # | Phase | Developer prompt (condensed) | Outcome |
|---|---|---|---|
| 1 | Planning | Shared the problem statement; asked for a step-by-step plan for a 3-tier solution with Python + FastAPI, MySQL and React in VS Code. | 3-tier architecture, entity list, business rules, edge-case strategy, API and page list, hour-by-hour timeline. |
| 2 | Planning | "Show me the folders in the three-tier architecture." | Folder tree grouped by tier (frontend / backend / database). |
| 3 | Planning | "First explain the complete problem statement so I understand it; then we go file by file, testing each file, then GitHub." | Plain-language explanation of the domain (zones, interlocks, alarms, floods, nuisance alarms, incidents, actions), the 5 edge cases, ground truth, evaluation criteria and an example event chain. |
| 4 | Setup | Project lives in `C:\CandidateWorkspace`; set up the GitHub repo first, then the 3-tier folders, then files. | Git init, `.gitignore`, remote, first push. |
| 5 | Setup | Tool check output (MySQL not on PATH); "I have MySQL Workbench with my own root user." | Created `safety_db` in Workbench; credentials kept in a git-ignored `.env`. |
| 6 | Setup | "Everything must be directly in C:\CandidateWorkspace, no extra folder." / "The frontend folder is missing." | Root-level layout; Vite React app created. |
| 7 | Setup | "I need backend with services, DTOs, routes, then a DB folder and a frontend folder - neat and clear." | Layered structure: `routes/ dto/ services/ repositories/ models/ core/`, `database/{schema,loader,seed,ground_truth,reports}`. |
| 8 | Setup | "Suggest a repo name" → connect to `plant-safety-event-analytics`. | Repo connected and pushed. |
| 9 | Backend core | "Go file by file - write a file, test it, then the next, so errors are fewer." | One-file-at-a-time workflow with a test command after every file. |
| 10 | Backend core | requirements.txt, `.env`, `config.py`, `database.py`, first pytest file - each tested. | Typed settings, safe MySQL URL, session/engine, 5 core tests passing. |
| 11 | Troubleshooting | `.gitignore` not ignoring `.env` (and a path mistake writing to `C:\`). | Recreated `.gitignore` as UTF-8 with an absolute path; verified with `git check-ignore`. |
| 12 | Generator | Question: "Are we storing the data in the DB?" | Explained generate-to-files → validate → load-to-MySQL, and why (exports, checksums, validation before load). |
| 13 | Generator | config, rules, id_factory, master_data, events, incidents, anomalies, exporter, run - each tested. | Seeded generator producing exactly 50,000 alarm events; identical checksum on Windows and Linux (`d40e71611fb01a97…`). |
| 14 | Validation | validate.py, reproducibility.py + tests. | 80 checks (75 PASS, 5 EXPECTED = labelled anomalies, 0 FAIL); two-run SHA-256 proof. |
| 15 | Repo hygiene | Git LF/CRLF warnings on generated files. | `.gitattributes` marks generated data `-text` so checksums survive checkout. |
| 16 | Product | "Everything the PS asks for should be visible in the frontend while running." | 12-page UI plan incl. a live PS checklist, validation, reproducibility, data-model and rules pages. |
| 17 | Database | schema.sql and loader. | 16 tables, 26 FKs, CHECK constraints, indexes; 112,815 rows loaded and verified against the manifest. |
| 18 | Backend API | "Go 5 files at a time, line by line - no zip." | Models, repositories, services (priority, floods, nuisance, repeated unsafe, trace, detection), DTOs, routes - tested per batch. |
| 19 | Backend API | "Give me the URLs to check in Postman and tell me if exceptions are handled properly." | Honest gap review, then global error handling (400/404/422/503/500, one JSON shape), input validation, 5 error tests; 28 normal + 12 error Postman URLs. |
| 20 | Troubleshooting | Import errors from files that contained code from another source. | Located the foreign names with `Select-String`; restored the tested versions; 39 tests passing. |
| 21 | Frontend | API client, hook, formatters, components, pages - 5 files at a time, each batch tested in the browser. | React talks to FastAPI (CORS) and shows backend errors readably. |
| 22 | Design | "UI is not trendy - make it unique." → then "I need rounded, curved, Segoe UI." | First an ISA-101 control-room theme; final design follows the developer's choice: modern rounded Segoe UI, colour reserved for abnormal conditions, hazard-stripe logo mark. |
| 23 | Run | "How do I run the frontend / stop the backend?" | Two-terminal workflow and troubleshooting table. |
| 24 | Docs | "Generate the .md files." | `build_docs.py` generates DATA_DICTIONARY, ERD (Mermaid), RULES and API docs from the schema, rules and OpenAPI. |
| 25 | Automation | "Make a run_all.py that runs everything and pushes the generated data to the DB directly." | One command: generate → validate → reproduce → load MySQL → docs → tests → refresh/serve API; all 6 steps OK in ~47 s. |
| 26 | Submission | "Give me the total README and a prompt history." | This file and the final README. |

## How the work was verified
* Every file was run or tested on the developer's machine before the next one was written.
* The assistant built and tested each part in its own sandbox first (Python 3.13 + MariaDB, Node 22 + headless Chrome
  screenshots of all 12 pages) so the code handed over was already proven to work together.
* Final state: 39 pytest tests passing, 80/80 validation checks, reproducible checksums across operating systems,
  27/27 problem-statement requirements shown live in the UI.

## Division of work
* **Developer:** problem framing, technology choices, environment and database setup, running and testing every file,
  Git/GitHub, design direction, final review and submission.
* **AI assistant:** plan and architecture proposal, code drafts, test commands, debugging guidance, documentation drafts.