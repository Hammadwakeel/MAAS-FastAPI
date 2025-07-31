from .prompt import chain
from .model import BusinessDescription, KeywordsResponse


def generate_keywords_service(input_data: BusinessDescription) -> KeywordsResponse:
    """Invoke the LangChain chain to generate keywords."""
    result: KeywordsResponse = chain.invoke({
        "business_description": input_data.description
    })
    return result