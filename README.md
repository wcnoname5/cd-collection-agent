# Smart CD Collection Assistant


This project is a **capstone project** for the [**Kaggle 5-Day AI Agents Intensive Course with Google**](https://www.kaggle.com/competitions/agents-intensive-capstone-project]),under the track *Concierge Agents*.


## 🎯 Project Goal & Motivation

I have a growing CD collection and want a clear, searchable record of what I own.
Manually typing all CD details is tedious and error-prone, so this project aims to build a simple AI agent that streamlines the process.
By using the **Discogs API** to fetch reliable metadata, the agent can speed up cataloging, reduce manual input, and make searching more accessible and accurate.

## 🧩 Current Scope

* **Add CDs** to the collection through natural-language prompts
* **Search CDs** by title, artist, genre, year, and more
* **Store and update** collection data in a structured format (currently using Google Sheets)

These core features form the foundation.
Further extensions (advanced metadata enrichment, automation workflows, analytics, etc.) may come later but are **not included in the initial version**.

## Status

Initial development — focusing on adding items to the collection and searching through them.

## **Project Structure**

Root layout (important files and folders):

```
.
├── config/           # optional config files (currently empty)
├── data/             # project data (empty)
├── main.py           # top-level launcher / demo
├── music_agent/      # agent code and tools
│   ├── __init__.py
│   ├── cd_agent.py
│   ├── prompt.py
│   ├── discogs_ingest_CLI.py
│   ├── sub_agents/  # sub-agents tools
│   │   ├── cd_info_summary_agent/
│   │   └── cd_search_agent/
│   └── tools/
│       ├── __init__.py
│       ├── add_cd_to_sheets_tool.py
│       ├── check_collection_for_cd_tool.py
│       ├── discogs_API_functions.py
│       ├── discogs_ingest_CLI.py
│       └── gsheets_API_functions.py
├── README.md
└── tests/             # unit/integration tests (currently empty)

```

Notes:
- The `music_agent` package contains the agent definition and the small tools that perform Discogs lookups and Google Sheets writes.
- `env/` is a checked-in Conda environment in this repository — activate it before running code: `eval "$(conda shell.bash hook)" && conda activate ./env`.
- Credentials: `gcp_credentials.json` (service account) and any Discogs token should be added to the environment or `.env` file before running scripts that access external APIs.

If you'd like, I can expand this tree to include more files, remove environment artifacts from the repository, or reorganize the code into an `agents/` package + `tools/` directory for clarity.
