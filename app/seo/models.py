from pydantic import BaseModel
from typing import Any, Dict

class SEORequest(BaseModel):
    seo_data: Dict[str, Any]
