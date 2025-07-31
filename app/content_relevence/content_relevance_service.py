# app/content_relevance/content_relevance_service.py
"""
Business logic service for Content Relevance analysis and prioritization (mirroring SEOService).
"""
import os
import getpass
import logging
from typing import Dict, Any

from app.page_speed.config import settings
from app.content_relevence.models import Recommendation, PrioritySuggestions
from app.content_relevence.prompts import ContentRelevancePrompts

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Module-level logger
glogger = logging.getLogger(__name__)


class ContentRelevanceService:
    """
    Service class for generating Content Relevance reports and prioritized suggestions via Gemini.
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

        # Prompt template for raw report
        self.report_prompt = ChatPromptTemplate.from_messages([
            ("system", ContentRelevancePrompts.REPORT_PROMPT),
            ("human", "{data}")
        ])

        # Prompt + parser for prioritized suggestions
        self.parser = PydanticOutputParser(pydantic_object=Recommendation)
        priority_template = ChatPromptTemplate.from_messages([
            ("system", ContentRelevancePrompts.SYSTEM_PROMPT),
            ("human", "{report}")
        ]).partial(format_instructions=self.parser.get_format_instructions())
        self.priority_chain = priority_template | self.llm | self.parser

    def generate_content_relevance_report(self, data: Dict[str, Any]) -> str:
        """
        Generate a Markdown Content Relevance report.
        """
        glogger.info("Starting Content Relevance report generation via llm.invoke.")
        if not self.gemini_api_key:
            raise Exception("Gemini API key not configured")

        try:
            report = (self.report_prompt | self.llm).invoke({"data": data})
            text = getattr(report, 'content', None) or getattr(report, 'text', None)
            if not text:
                raise Exception("Empty response from Gemini via llm.invoke")
            glogger.info("Content Relevance report generated successfully.")
            return text.strip()
        except Exception as e:
            glogger.error("Error generating content relevance report: %s", e, exc_info=True)
            raise

    def generate_content_priority(self, report: str) -> PrioritySuggestions:
        """
        Generate prioritized content relevance suggestions from a Markdown report.
        """
        glogger.info("Generating prioritized content relevance suggestions via chain.invoke.")
        try:
            rec: Recommendation = self.priority_chain.invoke({"report": report})
            return rec.priority_suggestions
        except Exception as e:
            glogger.error("Error generating content priority suggestions: %s", e, exc_info=True)
            raise
