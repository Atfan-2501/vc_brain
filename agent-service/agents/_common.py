"""Shared OpenAI structured-output caller. Every agent goes through here so logging
and JSON parsing live in one place."""
import json
import config
from schemas import SYSTEM_BOILERPLATE


def call_structured(name: str, schema: dict, user_content, extra_system: str = "",
                    multimodal_images: list[str] | None = None) -> dict:
    """Call OpenAI with a JSON schema and return the parsed dict.
    user_content: str, or a list of content parts for multimodal (deck images)."""
    client = config.openai_client()
    system = SYSTEM_BOILERPLATE + ("\n" + extra_system if extra_system else "")

    if multimodal_images:
        parts = [{"type": "text", "text": user_content if isinstance(user_content, str) else ""}]
        for img in multimodal_images:
            parts.append({"type": "image_url", "image_url": {"url": img}})
        user_msg = {"role": "user", "content": parts}
    else:
        user_msg = {"role": "user", "content": user_content}

    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[{"role": "system", "content": system}, user_msg],
        response_format={"type": "json_schema",
                         "json_schema": {"name": name, "schema": schema, "strict": True}},
    )
    return json.loads(resp.choices[0].message.content)
