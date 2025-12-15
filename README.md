# CS 651 Final Project: The Science of WildChat & MCP Agent

**Team Members:** Minsi Lu, Suky Zhang  


## 📖 Project Overview

This repository constitutes our final deliverable for CS 651. It addresses both key requirements of the project through a unified exploration of the **WildChat Dataset** (1.6M+ user-ChatGPT English interactions):

1.  **Data Science Insights (Addressing Point 2):** An introspective examination of the "Science of Human-AI Interaction," analyzing how users engage with LLMs, how topics evolve, and identifying behavioral archetypes.
2.  **MCP Implementation (Addressing Point 3):** The implementation of a **Model Context Protocol (MCP) Server**, transforming our static data insights into a dynamic, queryable agent that allows LLMs to "explore" the dataset autonomously.


## 📂 Repository Structure & Deliverables

```text
.
├── README.md                           # This file (Project Overview & Setup) 
├── insights/
│       ├── final project.ipynb         # [Point 2] Main Data Science Analysis Notebook
|       └── wildchat_analysis_mcp.ipynb # [Point 2/3] Bridge: From Insights to MCP Tool Design
├── server/                             # [Point 3] The MCP Server Implementation
├── pipeline/                           # [Extra] Advanced ETL & Hybrid Topic Modeling Scripts
│   └── ...
├── wildchat_clean.parquet              # Processed Data Sample
└── proposal 1.pdf

```
## Environment Setup
Option A: Using conda (Recommended)
```
conda create -n wildchat_mcp python=3.11
conda activate wildchat_mcp
pip install -r requirements.txt
```
Option B: Using standard venv
```
conda create -n wildchat_mcp python=3.11
conda activate wildchat_mcp
pip install -r requirements.txt
```
## 🔬 [Point 2] Data Science Insights (Requirement 2)


**Notebook:** [`final project.ipynb`](./final%20project.ipynb) 

Inspired by the "Science of Science" (an exploration of how science gets done), we conducted a scientific exploration of **how "Prompt Engineering" gets done**. Just as one might analyze ACM Fellows to understand Computer Science trends, we analyzed the **WildChat Dataset** (`allenai/WildChat-4.8M`) to understand the current state of Human-AI interaction.

**Dataset:**
* **Source:** [WildChat-4.8M on Hugging Face](https://huggingface.co/datasets/allenai/WildChat-4.8M)
* **Scale:** A massive public corpus of user-ChatGPT interactions, filtered and processed for this analysis.

**Key Research Questions:**
* **Prompt Topic Distribution:** —  What are the most common themes users discuss with LLMs? We categorized interactions into distinct domains such as *coding, creative writing, reasoning, and education* to visualize the landscape of user intent.
* **Content Distribution:** - What are the top 15 programming languages used by programmers, based on the volume of conversations? What are the top 15 types of programming errors that programmers most frequently fail to resolve on their own, based on error frequency?
* **Conversation Length and Engagement:** — How long are typical conversations? Are certain topics associated with longer or more interactive dialogues?
* **Model Comparison:** — Are there stylistic or structural differences between responses from different models (e.g., GPT-4 vs. Claude vs. Gemini)?

**Results:**
* ** Question1 **
Top 15 ask category：   
category
| Category            | Count |
|---------------------|-------|
| Creative Writing    | 82432 |
| Error               | 81613 |
| Roleplay            | 74593 |
| General Knowledge   | 52852 |
| Coding              | 39774 |
| Reasoning           | 17980 |
| Translation         | 10225 |
| Advice              | 8789  |
| Math                | 7285  |
| Data Analysis       | 5747  |
| Other               | 4851  |
| History             | 1056  |
| Travel              | 865   |
| Chemistry           | 809   |
| Science             | 805   |

Name: count, dtype: int64
* ** Question2 **
Top 15 ask languages:   
language
| Language     | Count |
|--------------|-------|
| Python       | 12786 |
| Javascript   | 5355  |
| English      | 4415  |
| Java         | 2839  |
| C#           | 2225  |
| C++          | 2201  |
| C            | 1189  |
| Vba          | 817   |
| Sql          | 576   |
| Lua          | 564   |
| Matlab       | 540   |
| Php          | 519   |
| Html         | 441   |
| Typescript   | 439   |
| R            | 418   |

Name: count, dtype: int64

Top 15 Error message：

error
| Error Message                                      | Count |
|---------------------------------------------------|-------|
| SyntaxError                                       | 467   |
| SyntaxError: invalid syntax                       | 89    |
| SyntaxError: unexpected EOF while parsing         | 24    |
| IndexError: list index out of range                | 22    |
| Segmentation fault                                | 14    |
| TODO                                              | 13    |
| undefined                                         | 10    |
| SyntaxError: EOL while scanning string literal     | 10    |
| java.lang.NullPointerException                    | 9     |
| IndentationError: expected an indented block       | 9     |
| TypeError: 'NoneType' object is not subscriptable  | 9     |
| SyntaxError: invalid character ‘’ in string        | 9     |
| SyntaxError: Unexpected end of input               | 8     |
| NameError: name 'name' is not defined              | 8     |
| wrong signals                                     | 8     |

Name: count, dtype: int64
* ** Question3 **
| Statistic | Num Turns | User Turns | Assistant Turns | Total Chars |
|----------:|----------:|-----------:|----------------:|------------:|
| count     | 3,199,860 | 3,199,860  | 3,199,860       | 3,199,860   |
| mean      | 3.229630  | 1.614815   | 1.614815        | 9,358.622   |
| std       | 5.081712  | 2.540856   | 2.540856        | 26,823.75   |
| min       | 2         | 1          | 1               | 1           |
| 50%       | 2         | 1          | 1               | 2,799       |
| 75%       | 2         | 1          | 1               | 6,333       |
| 90%       | 6         | 3          | 3               | 22,091      |
| 95%       | 10        | 5          | 5               | 45,466      |
| max       | 1,000     | 500        | 500             | 1,091,961   |

Most conversations are short, with a median of two total turns (one user turn and one assistant turn). However, a small fraction of conversations are significantly longer, as reflected by the heavy-tailed distribution in both turn counts and total character length.   
| Theme | Average Words per Text |
|------|------------------------|
| Infinity, Secrets, Truth & Relationships | 1457.6 |
| Musician Errors & City Context | 1409.7 |
| Jewelry, Women, Rings & Chains | 1234.9 |
| GPT Arguments, File Handling & Memory | 1126.5 |
| Device, Vectors & Include Statements | 836.2 |
| Baby Room & Personal Life Questions | 635.6 |
| Informal Dialogue & Casual Queries | 602.6 |
| Illegal or Fictional Dialogue Scenarios | 501.0 |
| Nail, Hair & DIY Art | 500.2 |
| Android Views, Products & Imports | 480.1 |

We analyze conversation length by measuring the average number of words in user texts for each topic.
The table above reports the top 10 topics with the longest average text length.

Several clear patterns emerge from this analysis.

First, topics related to abstract concepts and personal narratives, such as Infinity, Secrets, Truth & Relationships, exhibit the longest average text length. These conversations often involve storytelling, emotional reflection, or philosophical discussion, which naturally leads to long, detailed user inputs.

Second, creative and lifestyle-related topics, including Jewelry Design, Nail and Hair DIY Art, and Personal Life Questions, also show relatively long texts. These topics frequently require descriptive language and contextual background, resulting in higher word counts.

Third, technical topics, such as GPT Arguments, File Handling & Memory and Android Views and Imports, demonstrate substantial text length as well. This suggests that technical problem-solving often involves detailed explanations, code context, and iterative clarification, leading to longer user messages.

Overall, the results indicate that conversation length is strongly topic-dependent. Topics involving personal expression, creative description, or complex technical reasoning tend to generate significantly longer user texts than factual or transactional queries. This supports the conclusion that engagement and interaction depth vary systematically across topics.

* ** Question4 **

Here is the output :Comparison of response characteristics across different language models, including verbosity, lexical diversity, and structural features.

====== stylistic or structural differences from different models (average) ======

| Model          | Word Count | Lexical Diversity | Avg Word Length | Has Code | Has List |
|----------------|------------|-------------------|-----------------|----------|----------|
| gpt-3.5-turbo  | 112.0154   | 0.850464          | 6.755645        | 0.0036   | 0.0416   |
| gpt-4          | 266.6674   | 0.791679          | 6.975801        | 0.0026   | 0.0700   |
| gpt-4o         | 445.7236   | 0.798059          | 6.405032        | 0.0090   | 0.0568   |
| o1             | 306.8714   | 0.798521          | 6.489153        | 0.0280   | 0.0824   |


detailed data analysis saved as 'model_style_comparison.csv



====== simple result ======

1. model with longest conversation is : gpt-4o (445.7 words)

2. modes always contains code is : o1 (contribute to 2.8%)

3. model most repetively uses word is : gpt-4


**Methodology:**
* **Data Ingestion:** Loaded via the `datasets` library (`load_dataset("allenai/WildChat-4.8M")`).
* **Cleaning:** Filtered out "General/Noise" conversations (prompts <10 chars) to focus on substantive interactions.
* **Analytics:** Applied statistical aggregation on turn counts and topic frequencies. Because the conversation contains different languages, so I feed back the conversation into AI API to let AI generate the conversation topic and then I save the topic into a dataframe and count.
* **Visualization:** Generated distribution graphs for topics and temporal heatmaps to reveal engagement patterns.

## 🌉 [Point 2/3] From Insights to MCP Tool Design

**Notebook:** [`mcp_server/analysis/wildchat_analysis_mcp.ipynb`](./mcp_server/analysis/wildchat_analysis_mcp.ipynb)

This notebook acts as the **architectural bridge** between our data science insights and the final MCP Server implementation. Rather than deploying black-box code, we used this environment to **prototype, validate, and unit-test** every tool's logic against the live dataset.

**Design Philosophy: "Macro-Analytics, Micro-Inspection"**
To enable an LLM Agent to effectively navigate 1.6M+ records without context overflow, we engineered a hierarchical information retrieval funnel. This structure dictated the specific design of our MCP tools:

### 1. Meta-Analytics (The Map)
Before diving into specific data points, an agent must understand the dataset's shape, schema, and boundaries.
* **Logic:** Instead of scanning 30GB of data on-the-fly for basic counts, we query pre-computed metadata tables for O(1) latency.
* **Tools Prototyped:**  
    * `get_dataset_summary`: Provides instant access to total counts, date ranges, and distributions.
    * `get_db_schema`: Allows the LLM to understand table structures and column types to formulate accurate queries.

### 2. Macro-Analytics (The Compass)
Since the LLM cannot read 1.6M rows at once, these tools "compress" vast data into digestible statistical insights, enabling high-level pattern recognition.
* **Logic:** Aggregates data to quantify themes, compare model behaviors (e.g., GPT-4 vs. Claude), and visualize evolution over time.
* **Tools Prototyped:** 
    * `get_topic_stats`: Aggregates volume by topic for distribution analysis. Also allow LLM compares models' topic difference.
    * `get_engagement_stats`: Compares models based on structural metrics like turn count and verbosity.
    * `get_temporal_trends`: Tracks how user interests and model usage evolve over time.

### 3. Discovery Layer (The Navigation)
Aggregate stats are insufficient for qualitative analysis. This layer helps the agent find the "needle in the haystack"—specific examples that explain the trends.
* **Logic:** Utilizes **Full-Text Search (FTS)** with BM25 ranking for semantic retrieval and statistical methods for outlier detection.
* **Tools Prototyped:**
    * `search_conversations`: Finds specific concepts (e.g., "Segmentation Faults") using keyword search.
    * `detect_conversation_anomalies`: Identifies edge cases like potential jailbreaks (length outliers) or hallucinations (rare topics).
    * `analyze_user_behavior`: Segments users into archetypes like "Power Users" or "Specialists."

### 4. Micro-Inspection (Ground Truth)
This layer represents "Walking the Territory", validating hypotheses by reading actual dialogue. Without this, analysis remains theoretical.
* **Logic:** Retrieving full conversation logs to verify context (e.g., confirming if a "long conversation" is a creative writing prompt or a jailbreak attempt).
* **Tool Prototyped:** `get_conversation_content` for retrieving raw JSON logs by ID.

### 5. Ad-Hoc Autonomy (The Sandbox)
To address unanticipated questions that pre-defined functions cannot cover (the remaining edge cases), we implemented a safety-sandboxed SQL execution environment.
* **Tool Prototyped:** `run_sql_query`: Empowers the LLM to write and execute its own read-only SQL queries for complex, multi-step logic not covered by standard tools.


## 🛠️ [Point 3] MCP Implementation 
**Demo Video:** [🔗 Click Here to Watch the Demo](YOUR_VIDEO_LINK_HERE)  
**Dataset on HuggingFace:** [🔗 WildChat-CS651](https://huggingface.co/datasets/luminlemon/wildchat-cs651/tree/main)

While the previous section detailed the *design logic* and content of our tools, this section focuses on the **system architecture and engineering pipeline** required to make those tools performant. We utilize a **Local Server + Claude Desktop** architecture, where the MCP server runs locally on the user's machine (accessing the local DuckDB instance) and connects to Claude via `stdio`.

### Configuration

The system is controlled via a central configuration file to manage paths and performance tuning.

```python
# config.py
DB_FILE = "data/wildchat.db"          # Local DuckDB instance
HF_DATASET = "allenai/WildChat-4.8M"  # Upstream Data source
BATCH_SIZE = 10000                    # Optimized for limited RAM
```
### 1. The Data Pipeline (ETL)

To transform 1.6M raw logs into a queryable knowledge base, we implemented a robust 4-stage ETL pipeline.

#### **Stage 1: Ingestion (`ingest.py`)**
We stream data directly from Hugging Face (`streaming=True`) to avoid local disk bottlenecks.
* **Model Standardization:** Maps fragmented version names (e.g., `gpt-4-0314`, `gpt-4-1106-preview`) into unified **Model Families** (e.g., `gpt-4`, `gpt-4o`) using a predefined `MODEL_META_MAP`.
* **Data Cleaning:** Normalizes timestamps, estimates token counts, and filters out non-English or corrupted records.

#### **Stage 2: Hybrid Topic Modeling (`topic_modeling.py`)**
A sophisticated pipeline that goes beyond simple keyword matching.
1.  **Embeddings:** Generates vector embeddings for conversations using `all-MiniLM-L6-v2`.
2.  **Clustering:** Reduces dimensionality (PCA) and clusters conversations using `MiniBatchKMeans`.
3.  **LLM Labeling (Ollama Integration):**
    * Instead of numeric Cluster IDs (e.g., "Cluster 5"), we use a local **Qwen2.5-7B** model via **Ollama**.
    * The script feeds the top keywords and sample documents to Qwen, which generates human-readable labels (e.g., renaming a cluster full of `div`/`span` keywords to *"Web Development"*).
4.  **Performance Optimization (CTAS):** Updating 1.6M rows in-place is slow, because the data is stored in columnar format. We use the **CTAS (Create Table As Select)** strategy to rewrite the entire table with new topics in seconds rather than minutes.

#### **Stage 3: Indexing (`create_indices.py`)**
Optimizes the database for the two distinct search patterns of the MCP Agent:
* **B-Tree Indexes:** Created on `topic`, `model_family`, `timestamp`, and `country`. These provide **O(log n)** performance for the agent's filtering tools.
* **Full-Text Search (FTS):** Uses DuckDB's `fts` extension to build an inverted index on `search_text`. This enables **BM25 relevance ranking**, allowing the agent to find "needles in the haystack" (e.g., specific error messages or concepts) instantly.

#### **Stage 4: Meta-Precomputation (`create_meta.py`)**
* **Purpose:** Latency reduction for the Agent's "Initialization" phase.
* **Mechanism:** Pre-calculates total row counts, date ranges, and top-level distributions into a tiny `dataset_meta` table.
* **Result:** The `get_dataset_summary` tool returns in **O(1)** time (microseconds).

To reproduce the full database build locally (requires ~50GB disk space + Nvidia GPU for clustering):
```bash
# ================= PHASE 1: Heavy Processing =================
# (Skip this phase if you downloaded 'luminlemon/wildchat-cs651' in https://huggingface.co/datasets/luminlemon/wildchat-cs651/tree/main)

# 1. Ingest Data (Streams ~1.6M rows)
python pipeline/ingest.py

# 2. Start Local LLM Server (Required for Topic Labeling)
# Ensure Ollama is running in the background
ollama serve
ollama pull qwen2.5:7b

# 3. Run Hybrid Topic Modeling (Embeddings -> Clustering -> Qwen Labeling)
python pipeline/topic_modeling.py

# ================= PHASE 2: Optimization =================
# (Run these steps to optimize the database, even if downloaded)

# 4. Build Performance Indexes (B-Tree + FTS)
python pipeline/create_indices.py

# 5. Pre-compute Metadata
python pipeline/create_meta.py
```

###


### 2. Connecting to Claude Desktop

To use the WildChat MCP server locally with Claude Desktop, we utilize the `stdio` transport. This allows Claude to spawn your Python script as a subprocess and communicate with it directly.

**Configuration Steps:**

1.  Open Claude Desktop.
2.  Go to **Claude** -> **Settings** -> **Developer**.
3.  Click **Edit Config**. This opens the `claude_desktop_config.json` file.
4.  Add the `wildchat-local` configuration under the `mcpServers` section.

> **Note:** You must use the absolute path to the Python executable in your environment (e.g., Conda) to ensure all dependencies (`duckdb`, `pandas`, `fastmcp`) are loaded correctly. You can find this by running `which python` in your terminal.

```json
{
  "mcpServers": {
    "wildchat-local": {
      "command": "/absolute/path/to/your/conda/env/bin/python",
      "args": [
        "/absolute/path/to/cs651-final/server/server.py"
      ]
    }
  }
}
```
### 3. MCP Server Architecture

The server is structured modularly to separate tool logic, resource access, and prompt engineering.

#### **Component Breakdown**

* **`server.py` (Entry Point):**
    * Initializes the `FastMCP` application.
    * Acts as the central registry, importing functions from other modules and exposing them as MCP primitives (`@mcp.tool`, `@mcp.resource`, `@mcp.prompt`).
    * Manages the lifecycle of the DuckDB connection.

* **`tools.py` (Functional Logic):**
    * Contains the core Python implementation of our analytical layers (Meta, Macro, Discovery, Micro).
    * Each function here (e.g., `get_topic_stats`, `search_conversations`) connects to DuckDB, executes optimized SQL, and returns JSON strings formatted for the LLM. All the tool's design we introduce in part [point 2/3]()

* **`resources.py` (Direct Data Access):**
    * Implements URI-based data retrieval (`wildchat://...`).
    * Unlike tools which compute answers, resources allow the LLM to *read* raw data directly (e.g., reading the full database schema or a specific conversation log) as context.

* **`prompts.py` (System Prompts):**
    * Defines dynamic system prompts to prime the Agent.
    * `analyze-wildchat` primes the model to act as a Data Scientist, while `audit-conversation` primes it to act as a Safety Auditor.
---
