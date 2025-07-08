"""
Business logic services for PageSpeed analysis.
"""
import json
import requests
import logging
import google.generativeai as genai
from typing import Dict, Any
from app.page_speed.config import settings

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
        Create the specialized prompt for Gemini analysis in a human-readable format.

        Args:
            pagespeed_data (Dict[Any, Any]): PageSpeed Insights data

        Returns:
            str: Human-readable, user-friendly report prompt
        """
        logger.debug("Building Gemini analysis prompt from PageSpeed data.")
        return f"""
<<<<<<< HEAD:app/services.py
    You are an **Expert Web Performance Optimization Consultant**. The following JSON `{pagespeed_data}` contains exactly these keys (all required):
=======
    You are an **Expert Web Performance Optimization Consultant**. The following JSON `{{pagespeed_data}}` includes detailed website performance metrics from Google PageSpeed Insights.
>>>>>>> 574c6ac (Update endpoints):app/page_speed/services.py

    Your task is to analyze this data and generate a human-friendly performance **report in plain English**. The report will be read by a **non-technical business owner**, so keep it understandable while explaining technical concepts briefly when necessary.

    ### Format of Your Response:
    Respond with a **natural language summary (not JSON)**. It should read like a report, not like code or technical output.

    ---

    ### Your report must include the following sections:

    1. **Overall Performance Summary**
    - Explain how fast the website feels to users.
    - Mention the overall category (FAST, AVERAGE, SLOW) and what that means.
    - If origin data differs from page data, point it out.

    2. **Key Metrics Breakdown**
    - For each metric (`CLS`, `TTFB`, `FCP`, `INP`, `LCP`, `TBT`):
        - Provide the value and performance category (e.g., "good", "needs improvement").
        - Briefly explain what the metric means and how it impacts the user experience.
        - Use simple analogies if possible. (Example: “CLS measures layout shift – like if buttons jump around while loading.”)

    3. **Top Issues**
    - List and explain the top 3–5 performance problems in plain language.
    - Avoid jargon. Example: “Too many large images are slowing down the page.”

    4. **Improvement Opportunities**
    - Suggest high-impact actions to improve speed (e.g., compress images, lazy load below-the-fold content).
    - Prioritize based on effort (low/medium/high) and expected time savings.
    - Mention technical fixes where helpful, but **always** explain what they do and **why they help**.

    5. **Detailed Audit Notes**
    - Mention any specific URLs or files causing problems (e.g., slow scripts, unoptimized images).
    - For each, explain the issue and estimated time it adds to loading.
    - Be clear and concise.

    6. **Recommended Action Plan**
    - Provide a to-do list of concrete fixes with estimated effort levels.
    - If possible, include tips tailored to platforms (e.g., for WordPress or Next.js).

    7. **Ongoing Monitoring Advice**
    - Recommend how often they should check performance.
    ---

    ### Important:
    - Do **not** output JSON or code blocks unless specifically required.
    - Use a tone that's **professional, helpful, and non-technical**.
    - Help the reader understand what needs fixing and why it matters for their website and users.

    Example phrasing:
    > "Your site currently loads in about 3.2 seconds for most users, which is considered average. Improving this can reduce bounce rates and improve conversions."

    Be specific and practical. Use values directly from `{{pagespeed_data}}` such as `numeric_value`, `percentile`, and `category` fields.

    ### PageSpeed Data:
    {json.dumps(pagespeed_data, indent=2)}
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
5. **Code Snippet:** Provide a ready‑to‑copy snippet if applicable (e.g., `<img loading="lazy" src=...>`).
6. **Category Tag:** Prefix with optimization domain `[Image]`, `[CSS]`, `[JS]`, `[Server]`.
7. **Platform Tip:** If known, include stack‑specific advice (e.g., Next.js `next/image`).
8. **Priority Classification:**
   - High: Savings ≥ 1.5 seconds or score < 0.25
   - Medium: Savings between 0.5 and 1.49 seconds or score 0.25 to 0.50
   - Low: Savings < 0.5 seconds or score between 0.51 and 1.0
   - Unknown: No savings or score data available
9. Explain in easy english, avoiding technical jargon and explaination for technical terms.

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

