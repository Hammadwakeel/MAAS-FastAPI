"""
Business logic services for PageSpeed and SEO analysis.
"""
import json
import requests
import logging
import google.generativeai as genai
from typing import Dict, Any
from app.config import settings

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
You are an **Expert SEO Consultant** with deep expertise in on‑page, technical, and off‑page SEO.

The following JSON `{{SEO_DATA}}` contains exactly these keys (all required):

{json.dumps(seo_data, indent=2)}

Your task is to output **exactly** the following JSON report—no additional text, no extra keys, no commentary:

```json
{{
  "overall_score": integer,
  "grade": "A"|"B"|"C"|"D"|"F",
  "top_strengths": [string],
  "top_issues": [string],
  "metrics": [
    {{
      "name": string,
      "value": string|number|boolean|array,
      "benchmark": string,
      "score": integer,
      "status": "good"|"needs_improvement"|"critical",
      "why_it_matters": string,
      "recommendation": string
    }}
  ],
  "action_plan": [
    {{
      "metric": string,
      "fix": string,
      "effort_level": "low"|"medium"|"high"
    }}
  ],
  "monitoring": {{
    "frequency": string,
    "methods": [string]
  }},
  "technical_seo": "data_unavailable" | {{
    "core_web_vitals": {{
      "LCP": string,
      "FID": string,
      "CLS": string
    }},
    "page_speed_score": integer,
    "lazy_loading": boolean,
    "security_headers": [string]
  }},
  "schema_markup": "data_unavailable" | {{
    "structured_data_types": [string],
    "valid": boolean
  }},
  "backlink_profile": "data_unavailable" | {{
    "referring_domains": integer,
    "toxic_links": integer,
    "recommendations": string
  }},
  "trend_comparison": "data_unavailable" | {{
    "previous_score": integer,
    "change": "increase"|"decrease"|"no_change",
    "comment": string
  }}
}}

Instructions:

Do not include any text before or after the JSON.

Evaluate SEO performance holistically across all provided data:

On‑Page SEO (titles, meta, headings, content, images, links)

Technical SEO (robots.txt, sitemap.xml, indexability, mobile‑friendly, HTTPS, URL structure)

Off‑Page SEO (backlink_profile)

Use deterministic scoring based on internal benchmarks:

SEO Score: ≤50=critical, 51–70=needs_improvement, >70=good

Meta Title length: 50–60 chars=good, <50 or >60=needs_improvement

H1 Tags: exactly 1=good, >1=needs_improvement, 0=critical

Heading Structure errors: any=critical

Image Alt Tags ratio: ≥90% good, 50–89% needs_improvement, <50% critical

sitemapXmlCheck: missing=critical

robotsTxtCheck: missing=critical

indexabilityCheck: false=critical

internalLinksCount: <5=needs_improvement

externalLinksCount: <2=needs_improvement

Advanced sections (technical_seo, schema_markup, backlink_profile, trend_comparison):

If the input data lacks these metrics, set the field value to "data_unavailable".

Otherwise, populate with real values (e.g., core web vitals, page speed score, backlink counts).

The action_plan must list the 5 weakest metrics by score, across all sections.

Set "monitoring.frequency" to:

"weekly" if any metric status is "critical" or "needs_improvement".

"monthly" if all metrics are "good".

Grading scale:

90–100: A

80–89: B

70–79: C

60–69: D

<60: F    
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
4. **Effort Estimate:** Add an effort estimate (e.g. `"Effort: Low (≈1 hr)"`).
5. **Code Snippet:** Provide a ready‑to‑copy example if applicable  
   (e.g. `<meta name="description" content="...">`).
6. **Category Tag:** Prefix with SEO domain—  
   `[On-Page]`, `[Technical]`, `[Off-Page]`, `[Local]`, `[Schema]`.
7. **Impact Score:** Append a simple impact rating (e.g. `"Impact: ⭐⭐⭐☆☆"`).
8. **Platform Tip:** If applicable, include CMS or framework advice  
   (e.g. `"WordPress: use Yoast SEO"`, `"Next.js: use next/head"`).
9. **Priority Classification:**  
- **High:** Any metric with score `"critical"` or < 60, or impact ≥ 10%.  
- **Medium:** Score 60–79 or impact 5–9%.  
- **Low:** Score 80–100 or impact < 5%.  
- **Unknown:** No score or impact data available.

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


