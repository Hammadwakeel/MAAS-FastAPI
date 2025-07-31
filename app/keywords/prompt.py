import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .model import KeywordsResponse

# Initialize LLM
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY not set in environment variables")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    max_tokens=500,
    timeout=60,
    max_retries=3,
    api_key=GOOGLE_API_KEY
)

# Set up parser
parser = PydanticOutputParser(pydantic_object=KeywordsResponse)

# Build prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert SEO strategist and content marketer.
Generate the **top 10** most relevant keywords and key phrases
that a business should target, based on the following description.

**IMPORTANT**:
- Return _only_ a JSON object with a single key, `keywords`.
- The value must be an array of strings.
- Do NOT include any markdown, bullet lists, commentary, or extra keys.
{format_instructions}
"""),
    ("user", "{business_description}")
]).partial(format_instructions=parser.get_format_instructions())

# Compose chain
chain = prompt | llm | parser
