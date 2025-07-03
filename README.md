# alpha-datapipeline

A modular Python data pipeline for log ingestion, LLM-based analysis, and (optionally) RAG chatbot demonstration.  
This pipeline is designed for real-time log monitoring, storage, and AI-powered analysis using Elasticsearch and Ollama with the Llama 3.1 8B model.

---

## Workflow Overview

1. **Folder Scanner** (`folder_scanner.py`):  
   Continuously monitors specified log directories for new log files and entries.

2. **Database Service** (`db_service.py`):  
   Handles storage of log data into Elasticsearch. Receives data from the folder scanner.

3. **LLM Analysis Service** (`llm_analysis_service.py`):  
   Retrieves unprocessed logs from Elasticsearch, analyzes them using the Llama 3.1 8B model via Ollama, and updates their status.

4. **RAG Chatbot Service** (`rag_chatbot_service.py`):  
   (Optional/Dummy) Demonstrates a retrieval-augmented generation chatbot.  
   _Note: This feature is now deprecated and has been replaced in another repository, but you should still run it for completeness._

5. **App Orchestrator** (`app.py`):  
   Coordinates or monitors the pipeline (depending on your implementation).

---

## Prerequisites

- **Python 3.8+**
- **Elasticsearch** (Cloud free trial; create a new account and update your API keys and endpoint URLs)
- **Ollama** ([Download here](https://ollama.com/download))
- **Llama 3.1 8B Model** (Install via Ollama: `ollama pull llama3:8b`)
- **Required Python packages** (see [Installation](#installation))

---

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/srinipalli/alpha-datapipeline.git
cd alpha-datapipeline
```

2. **Set up a virtual environment (recommended)**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```
> If `requirements.txt` is missing, install at least:  
> `pip install elasticsearch requests watchdog`  
> (and any others as used in your scripts)

4. **Install and set up Ollama**
- Download and install Ollama from [https://ollama.com/download](https://ollama.com/download)
- Pull the Llama 3.1 8B model:
  ```bash
  ollama pull llama3:8b
  ```

5. **Set up Elasticsearch**
- Create a new [Elastic Cloud](https://www.elastic.co/cloud/) free trial account.
- Update your Elasticsearch API key and endpoint URLs in your configuration files or environment variables as required by the code.

---

## How to Run the Pipeline

**You must run the following scripts in separate terminals, in any order:**

1. **Start the Folder Scanner**
```bash
python folder_scanner.py
```
- Monitors log folders for new logs and sends them to the database service.

2. **Start the Database Service**
```bash
python db_service.py
```
- Receives log data and stores it in Elasticsearch.

3. **Start the LLM Analysis Service**
```bash
python llm_analysis_service.py
```
- Fetches unprocessed logs from Elasticsearch, sends them to Ollama for Llama 3.1 8B analysis, and updates their status.

4. **Start the RAG Chatbot Service (Dummy)**
```bash
python rag_chatbot_service.py
```
- This is a placeholder. The actual RAG chatbot use case is now handled in another repository.

5. **(Optional) Start the App Orchestrator**
```bash
python app.py
```
- Use this for additional orchestration, monitoring, or as an entry point for future enhancements.

**Each script should be run in its own terminal window or process.**

---

## Configuration

- **Elasticsearch:**  
- Use a new Elastic Cloud free trial account.
- Update all API keys and endpoint URLs in the code/config to match your account.
- **Ollama:**  
- Ensure Ollama is running and the Llama 3.1 8B model is installed.

---

## Typical Data Flow

1. **folder_scanner.py** detects new logs → sends to **db_service.py**
2. **db_service.py** stores logs in Elasticsearch
3. **llm_analysis_service.py** fetches unprocessed logs from Elasticsearch → sends to Llama 3.1 8B via Ollama → stores analysis results back in Elasticsearch
4. **rag_chatbot_service.py** (dummy) runs for demonstration (no longer used for production)
5. **app.py** can be used for orchestration or monitoring

---

## Notes & Recommendations

- **Elasticsearch Free Trial:**  
- Each new trial requires a new account.
- Update all API keys and endpoints in your code when you switch accounts.
- **Ollama & Llama Model:**  
- Ollama must be running locally.
- The Llama 3.1 8B model must be downloaded before starting the LLM analysis service.

---

## Troubleshooting

- **Elasticsearch connection errors:**  
- Double-check your API keys and endpoint URLs.
- Make sure your trial account is active and not expired.
- **Ollama errors:**  
- Ensure Ollama is running and the model is installed (`ollama list` to check).
- **Folder scanning issues:**  
- Ensure the log folder path is correct and accessible.

---

## License

_No license specified yet. Add a LICENSE file to clarify usage rights._

---

## Contact

For questions or suggestions, please open an issue in this repository.

---

> _This README fully describes the workflow, setup, and usage of the alpha-datapipeline project as of July 2025._
