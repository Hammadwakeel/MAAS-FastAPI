# app/mobile_usability/service.py
import os
import logging
from typing import Dict, Any

# Optional project settings import (falls back to env var)
try:
    from app.page_speed.config import settings  # if present in your project
    GEMINI_KEY = getattr(settings, "gemini_api_key", None)
except Exception:
    GEMINI_KEY = None

from app.mobile_usability.models import Recommendation, PrioritySuggestions
from app.mobile_usability.prompts import MobilePrompts

# LangChain / Gemini wrapper imports (same style as your SEO module)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

glogger = logging.getLogger(__name__)


class MobileUsabilityService:
    """
    LLM-only service for generating mobile usability report and prioritized suggestions.
    This class requires a Gemini API key to be available (env var or settings).
    """

    def __init__(self):
        # require Gemini key
        key = GEMINI_KEY or os.getenv("GEMINI_API_KEY")
        if not key:
            msg = "Gemini API key not configured. Set settings.gemini_api_key or GEMINI_API_KEY env var."
            glogger.error(msg)
            raise RuntimeError(msg)

        self.gemini_api_key = key

        # initialize LLM wrapper (Gemini)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=3,
            api_key=self.gemini_api_key
        )

        # Prompt template for generating the multi-line mobile usability report
        self.report_prompt = ChatPromptTemplate.from_messages([
            ("system", MobilePrompts.Report_PROMPT),
            ("human", "Please generate a comprehensive mobile usability audit based on this data:\n\n{mobile_data}")
        ])

        # Parser + priority prompt for structured priority suggestions
        self.parser = PydanticOutputParser(pydantic_object=Recommendation)
        self.priority_chain = (
            ChatPromptTemplate.from_messages([
                ("system", MobilePrompts.SYSTEM_PROMPT),
                ("human", "{report}")
            ]).partial(format_instructions=self.parser.get_format_instructions())
            | self.llm
            | self.parser
        )

    def generate_mobile_report(self, mobile_data: Dict[str, Any]) -> str:
        """
        Generate a mobile usability audit report using Gemini LLM (raw multi-line string).
        Raises on failure.
        """
        glogger.info("Invoking Gemini to generate mobile usability report.")
        prompt_input = {"mobile_data": mobile_data}
        try:
            # Use the prompt template piped into the LLM (same pattern as your SEO module)
            prompt_with_llm = self.report_prompt | self.llm
            response = prompt_with_llm.invoke(prompt_input)
            if not response:
                raise RuntimeError("Empty response from Gemini for mobile usability report.")
            # response is typically an object with .content in your setup; keep same handling
            return getattr(response, "content", str(response)).strip()
        except Exception as e:
            glogger.error("Error generating mobile report via Gemini: %s", e, exc_info=True)
            raise

    def generate_mobile_priority(self, report: str) -> PrioritySuggestions:
        """
        Generate prioritized mobile-usability suggestions using LLM + PydanticOutputParser.
        Returns PrioritySuggestions Pydantic model instance.
        """
        glogger.info("Invoking Gemini to generate priority suggestions.")
        try:
            rec: Recommendation = self.priority_chain.invoke({"report": report})
            # `rec` is a Pydantic model (Recommendation); return the nested PrioritySuggestions
            return rec.priority_suggestions
        except Exception as e:
            glogger.error("Error generating priorities via Gemini: %s", e, exc_info=True)
            raise
