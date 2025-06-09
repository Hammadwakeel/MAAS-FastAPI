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
        # We do not log full JSON here to avoid huge payload in logs,
        # but we do log that prompt construction is happening.
        logger.debug("Building Gemini analysis prompt from PageSpeed data.")
        return (
            "**Role:** You are an **Expert Web Performance Optimization Analyst and Senior Full-Stack Engineer** "
            "with deep expertise in interpreting Google PageSpeed Insights data, diagnosing frontend and "
            "backend bottlenecks, and devising actionable, high-impact optimization strategies.\n\n"
            "**Objective:**\n"
            "Analyze the provided Google PageSpeed Insights JSON data for the analyzed website. "
            "Your primary goal is to generate a comprehensive, prioritized, and actionable set of strategies "
            "to significantly improve its performance. These strategies must directly address the specific "
            "metrics and audit findings within the report, aiming to elevate both Core Web Vitals "
            "(LCP, INP, CLS) and other key performance indicators (FCP, TTFB, TBT), and ultimately "
            "improve the `overall_category` to 'FAST' where possible.\n\n"
            "**Input Data:**\n"
            "The following JSON object contains the complete PageSpeed Insights report:\n"
            f"```json\n{json.dumps(pagespeed_data, indent=2)}\n```\n\n"
            "**Analysis and Strategy Formulation - Instructions:**\n\n"
            "1.  **Executive Performance Summary:**\n"
            "    * Begin with a concise overview of the website's current performance status based on the provided data.\n"
            "    * Highlight the `overall_category` for both `loadingExperience` (specific URL) and `originLoadingExperience` (entire origin).\n"
            "    * Pinpoint the current values and `category` (e.g., FAST, AVERAGE, SLOW) for each key metric:\n"
            "        * `CUMULATIVE_LAYOUT_SHIFT_SCORE` (CLS)\n"
            "        * `EXPERIMENTAL_TIME_TO_FIRST_BYTE` (TTFB)\n"
            "        * `FIRST_CONTENTFUL_PAINT_MS` (FCP)\n"
            "        * `INTERACTION_TO_NEXT_PAINT` (INP)\n"
            "        * `LARGEST_CONTENTFUL_PAINT_MS` (LCP)\n"
            "        * `total-blocking-time` (TBT) from Lighthouse.\n"
            "    * Identify any significant `metricSavings` opportunities highlighted in the Lighthouse `audits`.\n\n"
            "2.  **Deep-Dive into Bottlenecks & Audit Failures:**\n"
            "    * Systematically go through the `loadingExperience`, `originLoadingExperience`, and `lighthouseResult` (especially the `audits` section).\n"
            "    * For each underperforming metric or failed/suboptimal audit (e.g., Lighthouse scores less than 1, or `notApplicable` audits with clear improvement paths like `lcp-lazy-loaded`, `critical-request-chains`, `dom-size`, `non-composited-animations`), extract the relevant details, display values, and numeric values.\n\n"
            "3.  **Develop Prioritized, Actionable Optimization Strategies:**\n"
            "    For *each* identified performance issue or opportunity, provide the following:\n"
            "    * **A. Issue & Evidence:** Clearly state the problem (e.g., \"High Total Blocking Time,\" \"Suboptimal Largest Contentful Paint due to unoptimized image,\" \"Excessive DOM Size,\" \"Render-blocking resources in critical request chain\"). Refer directly to the JSON data points and audit IDs that support this finding (e.g., `audits['total-blocking-time'].numericValue`, `audits['critical-request-chains'].details.longestChain`).\n"
            "    * **B. Root Cause Analysis (Inferred):** Briefly explain the likely technical reasons behind the issue based on the data.\n"
            "    * **C. Specific, Technical Recommendation(s):** Provide detailed, actionable steps a development team can take. Be specific.\n"
            "    * **D. Targeted Metric Improvement:** Specify which primary and secondary metrics this strategy will positively impact (e.g., \"This will directly reduce LCP and improve FCP,\" or \"This will significantly lower TBT and improve INP.\").\n"
            "    * **E. Priority Level:** Assign a priority (High, Medium, Low) based on:\n"
            "        * Impact on Core Web Vitals.\n"
            "        * Potential for overall score improvement (consider `metricSavings`).\n"
            "        * Severity of the issue (e.g., 'SLOW' or 'AVERAGE' categories).\n"
            "        * Estimated implementation effort (favor high-impact, low/medium-effort tasks for higher priority).\n"
            "    * **F. Justification for Priority:** Briefly explain why this priority was assigned.\n\n"
            "4.  **Strategic Grouping (Optional but Recommended):**\n"
            "    If applicable, group recommendations by area (e.g., Asset Optimization, JavaScript Optimization, Server-Side Improvements, Rendering Path Optimization, CSS Enhancements).\n\n"
            "5.  **Anticipated Overall Impact:**\n"
            "    Conclude with a statement on the anticipated overall improvement in performance and user experience if the high and medium-priority recommendations are implemented.\n\n"
            "**Output Format:**\n"
            "Please structure your response clearly. Use headings, subheadings, and bullet points to enhance readability and actionability. For example:\n\n"
            "---\n"
            "## Executive Performance Summary\n"
            "* **Overall URL Loading Experience Category:** [e.g., AVERAGE]\n"
            "* **Overall Origin Loading Experience Category:** [e.g., AVERAGE]\n"
            "* **Key Metrics:**\n"
            "    * LCP: [Value] ms ([Category])\n"
            "    * INP: [Value] ms ([Category])\n"
            "    * ...etc.\n\n"
            "---\n"
            "## Prioritized Optimization Strategies\n\n"
            "### High Priority\n"
            "**1. Issue & Evidence:** [e.g., High Total Blocking Time (TBT) of 1200 ms - `audits['total-blocking-time'].numericValue`]\n"
            "    * **Root Cause Analysis:** [e.g., Long JavaScript tasks on the main thread during page load, likely from unoptimized third-party scripts or complex component rendering.]\n"
            "    * **Specific, Technical Recommendation(s):**\n"
            "        * [Action 1]\n"
            "        * [Action 2]\n"
            "    * **Targeted Metric Improvement:** [e.g., TBT, INP, FCP]\n"
            "    * **Justification for Priority:** [e.g., Directly impacts interactivity (INP) and is a significant contributor to a poor lab score.]\n\n"
            "**(Continue with other High, Medium, and Low priority items)**\n"
            "---\n\n"
            "**Ensure your analysis is based *solely* on the provided JSON data and your expert interpretation of it. "
            "Avoid generic advice; all recommendations must be tied to specific findings within the report. "
            "Do not add anything irrelevant in the report. Do not write text in the starting of the report**"
        )
    
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

            prompt = (
                "You are an expert web performance analyst.\n"
                "Extract and organize the optimization recommendations from the following performance report\n"
                "into a JSON object with exactly these keys: \"high\", \"medium\", \"low\", and \"unknown\".\n"
                "Each key’s value should be a list of suggestion strings.\n\n"
                "Important:\n"
                "- Respond with *only* a valid JSON object.\n"
                "- Do NOT include any commentary or explanation outside the JSON.\n\n"
                "Performance Report:\n"
                "```\n"
                + report +
                "\n```"
            )

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

