import json
import os
from datetime import datetime

from mistralai.models.chat_completion import ChatMessage
from services.knowledge_documents_service import KnowledgeDocumentsService
from utils.pipeline_helpers import model_chat
service = KnowledgeDocumentsService()

def map_references(results):
    unique = set()
    refs = []

    for r in results:
        key = (r["document_id"], r["page_number"])
        basename = os.path.basename(r["document_path"])
        uuid_part, original_filename = basename.split("_", 1)
        preview_url = f"/blobs/preview/{uuid_part}"

        # Ensure uniqueness
        if key in unique:
            continue
        unique.add(key)

        refs.append({
            "document_id": r["document_id"],
            "filename": original_filename,
            "path": r["document_path"],
            "url": preview_url ,
            "page": r["page_number"],
        })

    return refs

def extract_contents_for_analysis(results):
    return [
        {
            "filename":  r["document_path"].split("_", 1)[1].rsplit(".", 2)[0],
            "content": r["content"]
        }
        for r in results
    ]


def build_prompt(user_input, response_text):
    is_failure = '"status": "error"' in response_text or '"status": "empty_data"' in response_text
    if isinstance(response_text, list):
        formatted = ""
        for item in response_text:
            content = item.get("content", "")
            formatted += f"{content} \n"
        response_text = formatted

    if is_failure:
        return f"""
        User question:
        {user_input}

        Data is not available.

        Answer instructions:
        - Provide a very short and general answer based on the topic of the question.
        - Do NOT mention errors, API, empty data, status messages, or any technical details.
        - Do NOT add opinions, assumptions, or speculation.
        - Maximum 2 sentences.
        """
    else:
        return f"""
        User question:
        {user_input}

        Answer instructions:
        - Answer ONLY based on the reference data below.
        - If the information is not found, answer:
          "The requested information was not found in the provided data."
        - Do NOT add opinions, assumptions, speculation, or technical explanations.
        - Do NOT create additional summaries unless explicitly requested.
        - Maximum 3 sentences.

        Reference data:
        {response_text}
        """


def analyze_response(user_input, contents_for_llm, max_len=2000):
    prompt = build_prompt(user_input, contents_for_llm)

    if len(prompt) > max_len:
        prompt = prompt[:max_len]
    system_prompt_content = (
        "You are a document analysis assistant. "
        "Always respond in formal, clear, and concise Indonesian. "
        "Do NOT greet the user, introduce yourself, provide long conclusions, "
    )

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    return model_chat(
        messages,
        model="llama3-8b-cpt-sahabatai",
        temperature=0.2,
        # max_tokens=600,
        stop=["END_OF_ANSWER", "\n\n"],
        repetition_penalty=True
    )

def analyze_input_chat(enriched_user_input):
    system_prompt_content = """
    You are an assistant for document query analysis.

    MANDATORY RULES:
    1. The answer must be in formal and concise Indonesian.
    2. The answer must be based ONLY on the given user text.
    3. No opinions, speculation, inference, or additional analysis.
    4. No labels, points, scores, categories, or metadata of any kind.
    5. The final result must be a single short sentence/paragraph summarizing the user's main intent.
    6. If no information can be concluded, answer:
       "Informasi tersebut tidak ditemukan dalam dokumen yang disediakan."
    7. Maximum 3 sentences. No reasons, explanations, or additional narration.
    """

    prompt = f"""
    Summarize and restate the main intent of the following user query
    into a single very clear sentence or short paragraph,
    to be used as a document search query:
    {enriched_user_input}
    """

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    return model_chat(messages)


async def run_knowledge_pipeline_en(user_input: str, history: str):
    try:
        final_user_input = user_input

        if history:
            enriched_input = f"""
            Chat history:
            {history}

            User input:
            {user_input}
            """
            final_user_input = analyze_input_chat(enriched_input)

        results = await service.find_vector(final_user_input)

        references = map_references(results)
        contents_for_llm = extract_contents_for_analysis(results)

        answer = analyze_response(final_user_input, contents_for_llm)

        return {
            "status": "success",
            "date": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "references": references,
            "results": contents_for_llm,
            "output": answer,
        }

    except Exception as e:
        print("Error in the pipeline:", e)
        return {"status": "error", "message": str(e)}
