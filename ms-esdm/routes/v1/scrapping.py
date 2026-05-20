import asyncio
import re

from fastapi import APIRouter, Query, Depends

from services.auth_service import require_api_key
from utils.pipeline_helpers import load_examples, resolve_api_url, call_api, semantic_recommend_api_improved_async, \
    fetch_api_simple

router = APIRouter()

@router.get("")
async def scrapping(user_input: str = Query(None), limit: int = Query(10, ge=1), api_key: str = Depends(require_api_key)):
    """
    Scrap API data and return raw JSON.
    - If user_input provided, use recommended API.
    - If empty, scrap all APIs in examples_min.json.
    """
    body = None
    examples = load_examples()
    results = []
    api_calls = []
    current_index = 0

    # Determine APIs to scrape
    if user_input:
        # Recommend single API
        rec_raw, cache = await semantic_recommend_api_improved_async(
            user_input,
            examples,
            [],
            cache=None
        )

        api_list = rec_raw.get("recommended_api", [])

    else:
        api_list = [ex["url"] for ex in examples]

    method = rec_raw.get("method", "GET").upper()
    params = rec_raw["parameters"][current_index] or {}
    body = rec_raw["body"][current_index] or {}

    uuid_match = re.search(r"uuid\s*([a-zA-Z0-9\-]+)", user_input.lower())
    code_match = re.search(r"kode\s*([A-Z]{3,})|code\s*([A-Z]{3,})", user_input)
    id_match = re.search(r"id\s*(\d+)", user_input.lower())
    volcano_code = rec_raw.get("volcano_code")

    results = []
    api_calls = []
    failed_calls = []

    for api_url in api_list:
        if not api_url:
            continue

        resolved_url = resolve_api_url(api_url)
        print(f"{resolved_url} -> {api_url}")

        # --- your variable replacement logic (uuid, code, id, etc.) ---
        if "{uuid}" in resolved_url and uuid_match:
            resolved_url = resolved_url.replace("{uuid}", uuid_match.group(1))

        if volcano_code and body:
            if isinstance(body, list) and body and isinstance(body[0], dict):
                body[0]["code"] = volcano_code
            elif isinstance(body, dict):
                body["code"] = volcano_code

        if code_match and body:
            body["code"] = code_match.group(1) or code_match.group(2)

        if "{id}" in resolved_url and id_match:
            resolved_url = resolved_url.replace("{id}", id_match.group(1))

        loop = asyncio.get_running_loop()

        try:
            # call sync function in thread
            response_json = await loop.run_in_executor(
                None,
                fetch_api_simple,
                resolved_url
            )

            print(response_json)

            data_field = (
                response_json.get("data")
                if isinstance(response_json, dict) and "data" in response_json
                else response_json
            )

            # Only success goes into results
            api_calls.append(resolved_url)
            results.append(data_field)

        except Exception as e:
            # Skip, do not add into results
            print(f"❌ Failed: {resolved_url} -> {e}")

            failed_calls.append({
                "api_url": resolved_url,
                "error": str(e),
            })

            # Continue to next API (automatically happens)
            continue

    return {
        "count": len(results),
        "api_calls": api_calls,
        "failed_calls": failed_calls,
        "results": results,
    }

