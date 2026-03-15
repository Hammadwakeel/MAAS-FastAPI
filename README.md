# MaaS (Marketing as a Service) - AI-Powered Marketing Engine

An advanced **Marketing-as-a-Service (MaaS)** backend built with FastAPI. This engine automates comprehensive website audits and manages AI-driven Meta Ads campaigns by leveraging Retrieval-Augmented Generation (RAG) and generative AI agents.

## Project Demo

<div align="center">
  <video src="https://github.com/Hammadwakeel/MAAS-FastAPI/raw/main/MAAS.mp4" width="100%" controls>
    Your browser does not support the video tag.
  </video>
</div>

## Project Links

* **GitHub Repository:** [Hammadwakeel/MAAS-FastAPI](https://www.google.com/search?q=https://github.com/Hammadwakeel/MAAS-FastAPI)
* **Backend Framework:** FastAPI

---

## Detailed Key Features

### 1. Intelligent Website Audit Suite (RAG-Enabled)

Each module doesn't just provide a report; it initializes a **Context-Aware AI Consultant** using RAG. The system ingests the website's specific data into a vector database (Qdrant) so users can ask natural language questions about their results.

* **SEO Optimizer & Strategist:** Generates a full technical SEO audit (Meta tags, sitemap, indexing). The **AI Chatbot** helps users prioritize which "Low" or "Critical" issues to fix first.
* **Content Relevance & Semantic Analysis:** Analyzes the relationship between the URL's content and target industry keywords, identifying "Content Gaps" and suggesting specific topics to improve authority.
* **Performance & PageSpeed Engine:** Integrates with Google PageSpeed Insights API to pull Core Web Vitals. The AI provides code-level diagnostics for faster loading.
* **UI/UX & Accessibility Auditor:** Evaluates visual hierarchy and navigational flow to suggest layout improvements that increase conversion rates.
* **Mobile-First Usability:** Checks for viewport issues and mobile-specific rendering hurdles.

### 2. Meta Ads Automation & Creative Suite

Moves beyond simple templates by using **Agentic Workflows** to build entire marketing campaigns from scratch.

* **AI Persona Architect:** Generates deep psychographic profiles (Interests, Pain Points, Behaviors) that can be dynamically updated.
* **Multi-Variant Ad Copy:** Generates variations of **Headings** and **Descriptions** optimized for different psychological triggers.
* **AI Image Generation:** Utilizes Google GenAI to create visual assets tailored to the specific ad context.
* **Smart Budgeting:** Calculates recommended daily vs. lifetime spends based on campaign duration.

### 3. Competitive Intelligence

* **Benchmarking Engine:** Input a competitor's URL for a side-by-side comparison of SEO, PageSpeed, and UX scores.
* **Gap Analysis:** Identifies specific areas where the competitor is outperforming the user and provides a "Catch-up Strategy."

---

## 🛠 Tech Stack

| Category | Technology |
| --- | --- |
| **Backend** | Python, FastAPI, Uvicorn |
| **LLMs** | Google Gemini, Groq |
| **Orchestration** | LangChain, LangGraph |
| **Vector DB** | Qdrant (High-performance similarity search) |
| **Database** | MongoDB (Persistent chat history) |

---

## Folder Structure

```text
MAAS-FASTAPI
├── app/
│   ├── ads/                  # Meta Ads Persona & Creative logic
│   ├── content_relevence/    # Content audit & AI feedback
│   ├── keywords/             # Keyword research agents
│   ├── mobile_usability/     # Mobile optimization services
│   ├── page_speed/           # PageSpeed Insights integration
│   ├── rag/                  # Core RAG logic & Vector Store utilities
│   ├── seo/                  # Technical SEO auditing
│   ├── uiux/                 # UI/UX analysis services
│   └── main.py               # FastAPI Entry point

```

---

## Environment Variables

To run this project, you will need to add the following variables to your `.env` file:

**Google API Keys**

* `PAGESPEED_API_KEY`
* `GEMINI_API_KEY`

**MongoDB Configuration**

* `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_HOST`, `MONGO_DB`, `MONGO_COLLECTION`

**FastAPI Server Configuration**

* `HOST`, `PORT`, `DEBUG`

**Qdrant Configuration**

* `QDRANT_URL`, `QDRANT_API_KEY`

---

## Getting Started

1. **Clone the Repo:**

```bash
git clone https://github.com/Hammadwakeel/MAAS-FastAPI.git

```

2. **Install Dependencies:**

```bash
pip install -r requirements.txt

```

3. **Run the server:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080

```
