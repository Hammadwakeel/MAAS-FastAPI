"""
Business logic services for PageSpeed and SEO analysis.
"""
import json
import requests
import logging
import google.generativeai as genai
from typing import Dict, Any
from app.page_speed.config import settings

# Create a module-level logger
glogger = logging.getLogger(__name__)

class SEOService:
    """
    Service class for generating SEO reports via Gemini.
    """
    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        if self.gemini_api_key:
            glogger.info("Configuring Gemini AI for SEO reporting.")
            genai.configure(api_key=self.gemini_api_key)
        else:
            glogger.warning("No Gemini API key found. SEO reporting will fail if called.")

    def generate_seo_report(self, seo_data: Dict[str, Any]) -> str:
        """
        Generate an SEO audit report using Gemini AI.

        Args:
            seo_data (Dict[str, Any]): Collected SEO metrics in JSON format.

        Returns:
            str: JSON-formatted SEO report string

        Raises:
            Exception: If report generation fails
        """
        glogger.info("Starting SEO report generation.")
        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            glogger.error(msg)
            raise Exception(msg)

        prompt = self._create_seo_prompt(seo_data)
        glogger.debug("SEO prompt: %s...", prompt[:200])

        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            if not text:
                raise Exception("Empty response from Gemini")
            glogger.info("SEO report generated successfully.")
            return text.strip()
        except Exception as e:
            msg = f"Error generating SEO report: {e}"
            glogger.error(msg, exc_info=True)
            raise

    def _create_seo_prompt(self, seo_data: Dict[str, Any]) -> str:
        """
        Build the advanced prompt for SEO analysis based on the updated specialized template.
        """
        return f"""
You are an **Expert SEO Consultant** with advanced knowledge of on-page, technical, and off-page SEO.

Your task is to analyze this data and return a detailed SEO audit report as a **multi-line string** (not as JSON). Keep it structured, clear, and easy to read — for example, using sections, bullet points, and indentation.

Include these sections in your output:

---

**Overall Summary**
- Overall SEO Score: (0–100)
- Grade: A, B, C, D, or F
- Top Strengths: List the top 3–5 strong areas
- Top Issues: List the top 3–5 weak/problematic areas

---

**Metric Breakdown**
For each key metric in the data:
- Metric Name
- Value: ...
- Benchmark: ...
- Score: ...
- Status: good / needs improvement / critical
- Why It Matters: Explain simply
- Recommendation: What to fix or improve

---

**Action Plan**
List 5 weakest metrics and how to fix them:
- Metric: ...
  - Fix: ...
  - Effort Level: low / medium / high

---

**Monitoring Strategy**
- Frequency: weekly or monthly (based on severity of issues)
- Methods: Tools or techniques to track progress

---

**Technical SEO**
If data is available, include:
- Core Web Vitals (LCP, FID, CLS)
- Page Speed Score
- Lazy Loading Enabled
- Security Headers Present

If not available, just write “Technical SEO data not available.”

---

**Schema Markup**
If available:
- Types Detected
- Is Valid: Yes/No  
Else: “Schema markup data not available.”

---

**Backlink Profile**
If available:
- Referring Domains
- Toxic Links
- Recommendations to improve off-page SEO

---

**Trend Comparison**
If available:
- Previous Score
- Score Change (increase, decrease, or no change)
- Comment

---

### ⚙️ Scoring Rules Summary (for reference):

- SEO Score: ≤50 = critical, 51–70 = needs improvement, >70 = good
- Meta Title: 50–60 chars = good, else needs improvement
- H1 Tags: exactly 1 = good, 0 or >1 = needs improvement/critical
- Heading Errors: any = critical
- Image Alt Tags: ≥90% = good, 50–89% = needs improvement, <50% = critical
- sitemapXmlCheck / robotsTxtCheck: missing = critical
- indexabilityCheck: false = critical
- internalLinksCount: <5 = needs improvement
- externalLinksCount: <2 = needs improvement

Use these rules to calculate metric status and overall grade:
- 90–100 → A
- 80–89 → B
- 70–79 → C
- 60–69 → D
- <60 → F

SEO data provided in JSON format:
{seo_data}

"""

    def generate_seo_priority(self, report: str) -> Dict[str, Any]:
        """
        Generate a dictionary of prioritized performance recommendations based on the Gemini-generated report.

        Args:
            report (str): The Gemini-generated performance report

        Returns:
            Dict[str, Any]: Dictionary mapping priority levels to optimization suggestions

        Raises:
            Exception: If the priority generation fails
        """
        glogger.info("Generating prioritized suggestions from the Gemini report.")

        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            glogger.error(msg)
            raise Exception(msg)

        try:
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = f"""
You are an **Expert Web Performance Analyst & Optimization Engineer**.

Your task is to carefully analyze the provided PageSpeed Insights performance report.
Extract **all** optimization recommendations and organize them into a JSON object with exactly these keys:
  - "high"
  - "medium"
  - "low"
  - "unknown"

Extract and organize the optimization recommendations from the following performance report
into a JSON object with exactly these keys: \"high\", \"medium\", \"low\", and \"unknown\".
Each key’s value should be a list of suggestion strings.

Classification Rules:
1. **Metric Reference:** For each suggestion, cite the metric name and full JSON path  
   (e.g. `metrics[2].name == "Keyword Density"` or `metrics[6].value`).
2. **Benchmark Comparison:** Include both the **current value** and the **ideal benchmark**  
   (e.g. `"Current: 15 keywords, Ideal: 1–3% density"`).
3. **Impact Estimate:** Quantify expected SEO impact (e.g. `"+12% CTR"` or `"+0.5 page rank score"`).
4. **Code Snippet:** Provide a ready‑to‑copy example if applicable  
   (e.g. `<meta name="description" content="...">`).
5. **Category Tag:** Prefix with SEO domain—  
   `[On-Page]`, `[Technical]`, `[Off-Page]`, `[Local]`, `[Schema]`.
6. **Platform Tip:** If applicable, include CMS or framework advice  
   (e.g. `"WordPress: use Yoast SEO"`, `"Next.js: use next/head"`).
7. **Priority Classification:**  
- **High:** Any metric with score `"critical"` or < 60, or impact ≥ 10%.  
- **Medium:** Score 60–79 or impact 5–9%.  
- **Low:** Score 80–100 or impact < 5%.  
- **Unknown:** No score or impact data available.
8. Explain in easy english, avoiding technical jargon and explaination for technical terms.


Important:
- Respond with *only* a valid JSON object.
- Do NOT include any commentary or explanation outside the JSON.

Performance Report:
{report}
"""



            response = model.generate_content(prompt)
            raw = (response.text or "").strip()
            glogger.debug("Raw priority response: %s", raw[:500] + ("…" if len(raw) > 500 else ""))

            # Locate the JSON portion by finding the first '{' and the last '}'
            start = raw.find('{')
            end = raw.rfind('}')
            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in Gemini response")

            json_str = raw[start:end+1]
            glogger.debug("Extracted JSON string: %s", json_str)

            suggestions = json.loads(json_str)
            if not isinstance(suggestions, dict):
                raise ValueError("Parsed JSON is not a dictionary")

            # Ensure all expected keys exist
            for key in ("high", "medium", "low", "unknown"):
                suggestions.setdefault(key, [])

            glogger.info("Priority suggestions generated successfully.")
            return suggestions

        except json.JSONDecodeError as je:
            msg = f"Failed to parse JSON from Gemini response: {je}"
            glogger.error(msg, exc_info=True)
            raise Exception(msg)
        except Exception as e:
            msg = f"Error generating priority suggestions: {e}"
            glogger.error(msg, exc_info=True)
            raise


