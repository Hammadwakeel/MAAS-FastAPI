"""
Business logic services for PageSpeed analysis.
"""
import json
import requests
import logging
import google.generativeai as genai
from typing import Dict, Any
from app.config import settings

# Create a module-level logger
logger = logging.getLogger(__name__)


class PageSpeedService:
    """Service class for PageSpeed Insights operations."""
    
    def __init__(self):
        self.pagespeed_api_key = settings.pagespeed_api_key
        self.gemini_api_key = settings.gemini_api_key
        
        if self.gemini_api_key:
            logger.info("Configuring Gemini AI with provided API key.")
            genai.configure(api_key=self.gemini_api_key)
        else:
            logger.warning("No Gemini API key found. Gemini reporting will fail if called.")
    
    def get_pagespeed_data(self, target_url: str) -> Dict[Any, Any]:
        """
        Fetch data from the PageSpeed Insights API for the given URL.
        
        Args:
            target_url (str): The URL to analyze
            
        Returns:
            Dict[Any, Any]: PageSpeed Insights data
            
        Raises:
            Exception: If API request fails
        """
        logger.info("Starting PageSpeed fetch for URL: %s", target_url)
        if not self.pagespeed_api_key:
            msg = "PageSpeed API key not configured"
            logger.error(msg)
            raise Exception(msg)
            
        endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            "url": target_url,
            "key": self.pagespeed_api_key
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=60)
            response.raise_for_status()
            logger.info("Successfully fetched PageSpeed data for %s (status %s)", target_url, response.status_code)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            msg = f"HTTP error fetching PageSpeed data: {http_err}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)
        except requests.exceptions.RequestException as req_err:
            msg = f"Request exception fetching PageSpeed data: {req_err}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)
        except Exception as e:
            msg = f"Unexpected error in get_pagespeed_data: {e}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)
        
    
    def generate_report_with_gemini(self, pagespeed_data: Dict[Any, Any]) -> str:
        """
        Uses the Gemini model to generate a detailed report based on the PageSpeed Insights data,
        employing an advanced prompt for specialized analysis and recommendations.
        
        Args:
            pagespeed_data (Dict[Any, Any]): PageSpeed Insights data
            
        Returns:
            str: Generated performance optimization report
            
        Raises:
            Exception: If report generation fails
        """
        logger.info("Starting Gemini report generation.")
        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            logger.error(msg)
            raise Exception(msg)
        
        try:
            # Select a Gemini model
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = self._create_analysis_prompt(pagespeed_data)
            logger.debug("Generated Gemini prompt: %s", prompt[:200] + "…")
            
            response = model.generate_content(prompt)
            
            if response and hasattr(response, "text") and response.text:
                logger.info("Gemini report generated successfully.")
                return response.text
            elif response and response.candidates and response.candidates[0].finish_reason == "SAFETY":
                msg = "Report generation was blocked due to safety settings"
                logger.error(msg)
                raise Exception(msg)
            else:
                msg = "No report could be generated or the response was empty"
                logger.error(msg)
                raise Exception(msg)
                
        except Exception as e:
            msg = f"Error generating report with Gemini: {e}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)
    
    def _create_analysis_prompt(self, pagespeed_data: Dict[Any, Any]) -> str:
        """
        Create the specialized prompt for Gemini analysis.

        Args:
            pagespeed_data (Dict[Any, Any]): PageSpeed Insights data

        Returns:
            str: Formatted prompt for Gemini
        """
        logger.debug("Building Gemini analysis prompt from PageSpeed data.")
        return f"""
    You are an **Expert Web Performance Optimization Consultant**. The following JSON `{{PSI_DATA}}` contains exactly these keys (all required):

    ```
    {{
    "url": string,  // analyzed page URL
    "origin": string,  // origin domain
    "loading_experience": {{  // Chrome UX data for URL
        "overall_category": "FAST"|"AVERAGE"|"SLOW",
        "metrics": {{
        "CLS": {{ "percentile": number, "category": string }},
        "TTFB": {{ "percentile": number, "category": string }},
        "FCP": {{ "percentile": number, "category": string }},
        "INP": {{ "percentile": number, "category": string }}
        }}
    }},
    "origin_loading_experience": {{  // Chrome UX data for origin
        "overall_category": "FAST"|"AVERAGE"|"SLOW"
    }},
    "lighthouse_audits": [  // only audits with score <1 or notApplicable
        {{
        "id": string,  // audit identifier
        "numeric_value": number,  // ms or unit value
        "score": number|null,  // 0–1 or null if N/A
        "description": string,  // audit title/description
        "details": {{  // optional details for resource URLs
            "items": [ {{ "url": string }} ]
        }},
        "metric_savings_ms"?: number  // if available
        }}
    ]
    }}
    ```

    Your job: output **exactly** the following JSON report—no extra keys, no prose outside these structures:

    ```json
    {{
    "overall_score": integer,
    "grade": "A"|"B"|"C"|"D"|"F",
    "summary": {{
        "CLS": {{ "value": number, "category": string }},
        "TTFB": {{ "value": number, "category": string }},
        "FCP": {{ "value": number, "category": string }},
        "INP": {{ "value": number, "category": string }},
        "LCP": {{ "value": number, "score": number }},
        "TBT": {{ "value": number, "score": number }}
    }},
    "top_issues": [string],
    "top_opportunities": [string],
    "audits": [
        {{
        "id": string,
        "value": number,
        "score": number|null,
        "resource_url"?: string,  // first offending URL from details.items
        "status": "critical"|"needs_improvement"|"good",
        "recommendation": string,
        "expected_gain_s": number
        }}
    ],
    "action_plan": [
        {{
        "id": string,
        "fix": string,
        "platform_tip"?: string,  // e.g. Next.js `next/image` or WordPress-specific advice
        "effort": "low"|"medium"|"high"
        }}
    ],
    "monitoring": {{
        "frequency": string,
        "methods": [string],
        "ci_snippet"?: string  // optional GitHub Action or Lighthouse CI config
    }}
    }}``` 
    **Requirements:**
    - **Strict Mapping:** Every field derives from `{{PSI_DATA}}` (use JSON paths like `lighthouseResult.audits[...].numeric_value`).
    - **No Extra Text:** Only the JSON above.
    - **Tie to JSON Paths:** Include resource URLs via `details.items[0].url`.
    - **Exact Code Snippets:** Provide `<link rel="preload"...>` or `<script defer>` snippets.
    - **Quantify Impact:** Use `metric_savings_ms` for each audit to calculate `expected_gain_s`.
    - **Threshold Targets:** State target values, e.g. "Reduce LCP to ≤1200 ms".
    - **Platform‑Specific Tips:** If known, include stack advice, e.g. Next.js `next/image` or WordPress plugins.
    - **Monitoring CI:** Optionally include a GitHub Action snippet:
    ```yaml
    - uses: treosh/lighthouse-ci-action@v5
        with:
        configPath: .lighthouserc.json
    ```
    - **Deterministic Scoring & Priority:** Same as before.
    """

    
    def analyze_url(self, url: str) -> Dict[str, Any]:
        """
        Perform complete PageSpeed analysis for a given URL.
        
        Args:
            url (str): The URL to analyze
            
        Returns:
            Dict[str, Any]: Complete analysis results
        """
        try:
            # Fetch PageSpeed data
            pagespeed_data = self.get_pagespeed_data(url)
            
            # Generate report with Gemini
            report = self.generate_report_with_gemini(pagespeed_data)
            
            return {
                "success": True,
                "url": url,
                "report": report,
                "pagespeed_data": pagespeed_data,
                "error": None
            }
            
        except Exception as e:
            logger.error("Failed full analyze_url flow: %s", e, exc_info=True)
            return {
                "success": False,
                "url": url,
                "report": None,
                "pagespeed_data": None,
                "error": str(e)
            }
        
    def generate_priority(self, report: str) -> Dict[str, Any]:
        """
        Generate a dictionary of prioritized performance recommendations based on the Gemini-generated report.

        Args:
            report (str): The Gemini-generated performance report

        Returns:
            Dict[str, Any]: Dictionary mapping priority levels to optimization suggestions

        Raises:
            Exception: If the priority generation fails
        """
        logger.info("Generating prioritized suggestions from the Gemini report.")

        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            logger.error(msg)
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
1. **Audit Reference:** Cite the audit ID **and** full JSON path (e.g. `lighthouseResult.audits['unused-javascript'].details.items[0].url`).
2. **Measurable Target:** Include the numeric goal (e.g., "Reduce LCP to ≤1200 ms").
3. **Resource Context:** Embed the resource URL or file name when relevant.
4. **Expected Savings:** Append expected savings in seconds (from `metric_savings_ms`).
5. **Effort Estimate:** Add an effort estimate (e.g., "Effort: Medium (≈2 hrs)").
6. **Code Snippet:** Provide a ready‑to‑copy snippet if applicable (e.g., `<img loading="lazy" src=...>`).
7. **Category Tag:** Prefix with optimization domain `[Image]`, `[CSS]`, `[JS]`, `[Server]`.
8. **Impact Score:** Append a simple impact rating (e.g., "Impact: ⭐⭐⭐☆☆" or "% of total savings").
9. **Platform Tip:** If known, include stack‑specific advice (e.g., Next.js `next/image`).
10. **Priority Classification:**
   - High: Savings ≥ 1.5 seconds or score < 0.25
   - Medium: Savings between 0.5 and 1.49 seconds or score 0.25 to 0.50
   - Low: Savings < 0.5 seconds or score between 0.51 and 1.0
   - Unknown: No savings or score data available

Important:
- Respond with *only* a valid JSON object.
- Do NOT include any commentary or explanation outside the JSON.

Performance Report:
{report}
"""



            response = model.generate_content(prompt)
            raw = (response.text or "").strip()
            logger.debug("Raw priority response: %s", raw[:500] + ("…" if len(raw) > 500 else ""))

            # Locate the JSON portion by finding the first '{' and the last '}'
            start = raw.find('{')
            end = raw.rfind('}')
            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in Gemini response")

            json_str = raw[start:end+1]
            logger.debug("Extracted JSON string: %s", json_str)

            suggestions = json.loads(json_str)
            if not isinstance(suggestions, dict):
                raise ValueError("Parsed JSON is not a dictionary")

            # Ensure all expected keys exist
            for key in ("high", "medium", "low", "unknown"):
                suggestions.setdefault(key, [])

            logger.info("Priority suggestions generated successfully.")
            return suggestions

        except json.JSONDecodeError as je:
            msg = f"Failed to parse JSON from Gemini response: {je}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)
        except Exception as e:
            msg = f"Error generating priority suggestions: {e}"
            logger.error(msg, exc_info=True)
            raise

