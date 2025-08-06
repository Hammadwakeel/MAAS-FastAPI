from typing import Dict, Any
import os
import getpass
import logging
from app.uiux.models import Recommendation, PrioritySuggestions
from app.uiux.prompts import UIUXPrompts
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger(__name__)

class UIUXService:
    """
    Service class for generating UI/UX reports and prioritized suggestions via LLM.
    """
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            key = getpass.getpass("Enter your Gemini API key: ")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            api_key=key
        )

        # Report prompt template
        self.report_prompt = ChatPromptTemplate.from_messages([
            ("system", UIUXPrompts.REPORT_PROMPT),
            ("human", "Please generate a comprehensive UI/UX audit report based on the following data:\n\n{uiux_data}")
        ])

        # Priority suggestions parser
        self.parser = PydanticOutputParser(pydantic_object=Recommendation)
        self.priority_chain = (
            ChatPromptTemplate.from_messages([
                ("system", UIUXPrompts.SYSTEM_PROMPT),
                ("human", "{report}")
            ]).partial(format_instructions=self.parser.get_format_instructions())
            | self.llm
            | self.parser
        )

    def generate_uiux_report(self, uiux_data: Dict[str, Any]) -> str:
        logger.info("Generating UI/UX report via LLM...")
        prompt_input = {"uiux_data": uiux_data}
        response = self.report_prompt | self.llm
        result = response.invoke(prompt_input)
        return result.content.strip()

    def generate_uiux_priority(self, report: str) -> PrioritySuggestions:
        logger.info("Generating prioritized UX suggestions via chain...")
        rec: Recommendation = self.priority_chain.invoke({"report": report})
        return rec.priority_suggestions
