"""
Business logic services for PageSpeed and SEO analysis.
"""
import os
import getpass
import logging
from typing import Dict, Any
from app.page_speed.config import settings
from app.seo.models import Recommendation, PrioritySuggestions
from app.seo.prompts import SEOPrompts

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Module-level logger
glogger = logging.getLogger(__name__)

class SEOService:
    """
    Service class for generating SEO reports and prioritized suggestions via Gemini.
    """
    def __init__(self):
        # configure Gemini key
        key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            key = getpass.getpass("Enter your Gemini API key: ")
        self.gemini_api_key = key

        # initialize LangChain LLM wrapper
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=3,
            api_key=self.gemini_api_key
        )

        # Prompt template for raw SEO report
        self.report_prompt = ChatPromptTemplate.from_messages([
            ("system", SEOPrompts.Report_PROMPT),
            ("human", "Please generate a comprehensive SEO audit report based on the following data:\n\n{seo_data}")
        ])

        # Prompt + parser for prioritized suggestions
        self.parser = PydanticOutputParser(pydantic_object=Recommendation)
        self.priority_chain = (
            ChatPromptTemplate.from_messages([
                ("system", SEOPrompts.SYSTEM_PROMPT),
                ("human", "{report}")
            ]).partial(format_instructions=self.parser.get_format_instructions())
            | self.llm
            | self.parser
        )

    def generate_seo_report(self, seo_data: Dict[str, Any]) -> str:
        """
        Generate an SEO audit report using Gemini AI via llm.invoke.

        Args:
            seo_data (Dict[str, Any]): Collected SEO metrics in JSON-serializable format.

        Returns:
            str: Raw text SEO report

        Raises:
            Exception: If report generation fails
        """
        glogger.info("Starting SEO report generation via llm.invoke.")
        if not self.gemini_api_key:
            msg = "Gemini API key not configured"
            glogger.error(msg)
            raise Exception(msg)

        prompt_input = {"seo_data": seo_data}
        glogger.debug("Invoking LLM for SEO report with data keys: %s", list(seo_data.keys()))

        try:
            # llm.invoke returns the raw string response
            report_text: str = self.report_prompt | self.llm
            report = report_text.invoke(prompt_input)
            if not report:
                raise Exception("Empty response from Gemini via llm.invoke")
            glogger.info("SEO report generated successfully.")
            return report.content.strip()
        except Exception as e:
            msg = f"Error generating SEO report: {e}"
            glogger.error(msg, exc_info=True)
            raise

    def generate_seo_priority(self, report: str) -> PrioritySuggestions:
        """
        Generate prioritized SEO suggestions from a report via chain.invoke.

        Args:
            report (str): SEO report content

        Returns:
            PrioritySuggestions: Parsed, prioritized recommendations
        """
        glogger.info("Generating prioritized SEO suggestions via chain.invoke.")
        try:
            rec: Recommendation = self.priority_chain.invoke({"report": report})
            return rec.priority_suggestions
        except Exception as e:
            msg = f"Error generating priority suggestions: {e}"
            glogger.error(msg, exc_info=True)
            raise
