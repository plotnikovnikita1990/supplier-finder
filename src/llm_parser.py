import json
import os
from typing import Optional

from .models import SearchQuery

SYSTEM_PROMPT = """Ты парсер закупочных запросов. Верни только JSON.
Поля:
product: string|null
category: string|null
region: string|null
max_price: number|null
max_moq: number|null
certifications_required: boolean
delivery_required: boolean
hard_region: boolean
hard_certifications: boolean
Не выдумывай отсутствующие значения. hard_* ставь true только если пользователь явно делает условие обязательным.
"""

def parse_with_openai(text: str) -> Optional[SearchQuery]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        payload = json.loads(response.choices[0].message.content)
        return SearchQuery(raw_text=text, **payload)
    except Exception:
        return None
