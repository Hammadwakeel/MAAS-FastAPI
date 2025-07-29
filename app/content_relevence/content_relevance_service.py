# content_relevance_service.py
"""
Business logic service for Content Relevance analysis.
"""
import json
import logging
import google.generativeai as genai
from typing import Dict, Any
from app.page_speed.config import settings

# Create a module-level logger
glogger = logging.getLogger(__name__)

class ContentRelevanceService:
    """
    Service class for generating Content Relevance reports via Gemini AI.
    """
    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        if self.gemini_api_key:
            glogger.info("Configuring Gemini AI for Content Relevance reporting.")
            genai.configure(api_key=self.gemini_api_key)
        else:
            glogger.warning("No Gemini API key found. Reporting will fail if called.")

    def generate_content_relevance_report(self, data: Dict[str, Any]) -> str:
        """
        Generate a Content Relevance report using Gemini AI.
        """
        glogger.info("Starting Content Relevance report generation.")
        if not self.gemini_api_key:
            glogger.error("Gemini API key not configured")
            raise Exception("Gemini API key not configured")

        try:
            prompt = self._create_relevance_prompt(data)
            glogger.debug("Relevance prompt: %s", prompt[:200])
            response = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
            text = getattr(response, "text", None)
            if not text:
                glogger.error("Empty response from Gemini")
                raise Exception("Empty response from Gemini")
            glogger.info("Content Relevance report generated successfully.")
            return text.strip()
        except Exception as e:
            glogger.error("Error during report generation: %s", e, exc_info=True)
            raise

    def _create_relevance_prompt(self, data: Dict[str, Any]) -> str:
        """
        Build the enhanced prompt for Content Relevance analysis, including benchmarks, examples, and impact estimates.
        """
        keywords = data.get('keywords', [])
        keyword_list = ", ".join(keywords)
        return f"""
You are a **Content Strategy Expert**. Analyze the following content metrics and target keywords for relevance, coverage, and practical SEO impact. Provide a detailed report in Markdown, using structured sections do not add tables in the report, with the following enhancements:

1. **Summary of Relevance**:
   - Brief overview of alignment with keywords: {keyword_list}
   - Overall Content Relevance Score: {data.get('contentRelevanceScore')} (out of 10)

2. **Metric Breakdown**:
   For each metric below, include:
   - **Value** (from data)
   - **Benchmark** (ideal or industry standard)
   - **Status**: good / needs improvement / critical
   - **Why It Matters**: concise rationale
   - **Specific Example**: show where/how to improve (e.g., exact H1 text with keyword)
   - **Expected Impact**: estimated uplift (e.g., `+5% relevance`)

   - **Keyword Coverage Score**: {data.get('keywordCoverageScore')}
   - **Density Score**: {data.get('densityScore')}% (ideal 1–3%)
   - **Readability**: {data.get('readabilityScoreOutOf10')} / 10 (ideal ≥ 6)
   - **Word Count**: {data.get('wordCount')} words (benchmark 1500–3000)
   - **Media Richness**: Images = {data.get('imageCount')}, Videos = {data.get('videoCount')} (ideal ≥ 2 videos)

3. **Top Strengths**:
   - List top 3 areas where the actual values exceed benchmarks, referencing metric names and values.

4. **Key Issues & Recommendations**:
   For each of the top 3 issues, provide:
   - **Issue**: name and value vs. benchmark
   - **Actionable Fix**: code or content snippet example, e.g.:  
     ```html
     <h1>{keywords[0].capitalize()} Services for Your Business</h1>
     ```
   - **Effort**: low / medium / high
   - **Expected Impact**: e.g., `+10% coverage`, `+3 readability`

5. **Priority Action Plan**:
   - Top 5 actions, with columns: Priority (1–5), Action, Effort, Expected Impact.

6. **Monitoring & Next Steps**:
   - Weekly or monthly tracking recommendations

7. **Bonus**: Suggest 2 related long-tail keywords to enhance depth.

Make the report engaging, use code blocks, and bullet lists where appropriate. Do not output JSON—provide a human-readable Markdown report. and do not write anything outside the report format."""


    def generate_content_priority(self, report: str) -> Dict[str, Any]:
        """
        Generate prioritized content relevance recommendations based on the AI-generated report.

        Args:
            report (str): The Markdown-formatted content relevance report.

        Returns:
            Dict[str, Any]: Dictionary mapping priority levels to recommendation lists.

        Raises:
            Exception: If priority generation fails.
        """
        glogger.info("Generating prioritized suggestions from the content relevance report.")
        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            glogger.error(msg)
            raise Exception(msg)
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = f"""
You are a **Content Strategy Expert**. Extract all actionable recommendations from the following content relevance report and organize them into a JSON object with keys: "high", "medium", "low". 

For each recommendation, include:
- "recommendation": the action text
- "impact": the expected impact (e.g. "+5% relevance")
- "effort": low/medium/high

Important:
- Respond with *only* a valid JSON object.
- Do NOT include any commentary or explanation outside the JSON.
 of t

Report:
{report}

Respond with only a JSON object.
"""
            response = model.generate_content(prompt)
            raw = (response.text or "").strip()
            glogger.debug("Raw priority response: %s", raw[:200])
            # Extract JSON
            start = raw.find('{')
            end = raw.rfind('}')
            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in response")
            json_str = raw[start:end+1]
            suggestions = json.loads(json_str)
            if not isinstance(suggestions, dict):
                raise ValueError("Parsed JSON is not a dictionary")
            for key in ("high", "medium", "low", "unknown"):
                suggestions.setdefault(key, [])
            glogger.info("Priority suggestions generated successfully.")
            return suggestions
        except json.JSONDecodeError as je:
            msg = f"Failed to parse JSON: {je}"
            glogger.error(msg, exc_info=True)
            raise Exception(msg)
        except Exception as e:
            msg = f"Error generating content priority suggestions: {e}"
            glogger.error(msg, exc_info=True)
            raise