# Codex Execution Instructions

Read `MASTER_PROMPT.md` first, then every other `.md` file in this workspace.

Inspect the entire workspace before implementation.

Build the project completely. Do not stop at scaffolding.

For each major component:
1. implement
2. run
3. inspect
4. debug
5. test
6. continue

At the end:
- generate all synthetic datasets
- execute the complete pipeline
- populate the database
- calculate KPIs
- evaluate forecasting
- generate projected inventory
- generate exceptions
- export Power BI datasets
- run all tests
- smoke-test FastAPI
- inspect outputs
- remove unnecessary temporary files
- verify no secrets
- update documentation with actual results

If Power BI Desktop is unavailable, generate import-ready outputs and documentation instead of a fake PBIX.

If an LLM API is unavailable, implement and test the deterministic assistant fallback.

Do not ask the user to implement individual components unless a genuine environment limitation prevents progress. Make reasonable technical decisions and continue autonomously.

Do not claim anything was executed unless it was actually executed.
