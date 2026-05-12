"""
Eurika AI Agent - OpenCode Zen GPT-5-nano with tool use.
Searches the uploaded documents in ChromaDB to answer user questions.
"""

import json
import os
from typing import AsyncGenerator, Optional

import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenCode Zen API Configuration
OPENCODE_ZEN_BASE_URL = os.getenv("OPENCODE_ZEN_BASE_URL")
OPENCODE_ZEN_API_KEY = os.getenv("OPENCODE_ZEN_API_KEY")
OPENCODE_ZEN_MODEL_NAME = os.getenv("OPENCODE_ZEN_MODEL_NAME", "gpt-5-nano")

# ChromaDB client
chroma_client = chromadb.Client()

# System prompt for the agent
SYSTEM_PROMPT = """You are Eurika, an advanced, highly capable AI voice assistant.
You are speaking to the user over a live voice connection. Your responses must be conversational, concise, and completely free of markdown formatting, bullet points, or emojis.

Key Instructions:
1. Knowledge Base: ALWAYS use the `search_knowledge_base` tool to look up information if the user asks a question about the uploaded documents or specific knowledge.
2. Natural Delivery: When answering based on documents, do NOT say "Based on the document" or "I found this in your files". Just answer the question naturally and confidently.
3. Missing Information: If the answer cannot be found in the documents, honestly state that you don't have that information. Use the `log_unanswered` tool to track the gap.
4. Escalation: If the user is frustrated, requests a real person, or the task is highly complex, use the `escalate_to_human` tool.

Personality:
- Be warm, highly professional, and empathetic.
- Keep your answers brief. Since you are speaking, long answers are hard to follow. Give the direct answer first.
- Read acronyms naturally and avoid complex punctuation."""


def get_collection(session_id: str):
    """Get or create a ChromaDB collection for a session."""
    return chroma_client.get_collection(name=session_id)


def search_knowledge_base(session_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Search the knowledge base for relevant document chunks.

    Args:
        session_id: The session ID (collection name)
        query: The search query
        top_k: Number of top results to return

    Returns:
        List of relevant document chunks
    """
    try:
        collection = get_collection(session_id)
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        if results and results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []


# OpenAI/OpenRouter tool definitions for knowledge base tool use
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the uploaded documents to answer the user's question. Use this when the user asks about information from their uploaded files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - what to look for in the documents"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Transfer the conversation to a human agent. Use when the question is too complex, sensitive, or requires human intervention.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "The reason for escalating to a human"
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_unanswered",
            "description": "Log a question that could not be answered from the documents. Use when the user's question cannot be answered from the uploaded files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question that could not be answered"
                    }
                },
                "required": ["question"]
            }
        }
    }
]


def mask_api_key(key: str) -> str:
    if not key:
        return "<missing>"
    if key.startswith("Bearer "):
        key = key.split(" ", 1)[1]
    return f"{key[:6]}...{key[-4:]}"


def execute_tool(tool_name: str, tool_input: dict, session_id: str) -> str:
    """
    Execute a tool and return the result.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Arguments for the tool
        session_id: The session ID for knowledge base access

    Returns:
        Tool execution result as string
    """
    if tool_name == "search_knowledge_base":
        chunks = search_knowledge_base(session_id, tool_input["query"])
        if chunks:
            return "\n\n".join(chunks)
        return "No relevant information found in the documents."

    elif tool_name == "escalate_to_human":
        # Log escalation (could be stored to file or sent elsewhere)
        print(f"Escalation requested: {tool_input['reason']}")
        return "I'm connecting you with a human agent. Please hold..."

    elif tool_name == "log_unanswered":
        # Log unanswered question (could be stored to file)
        print(f"Unanswered question: {tool_input['question']}")
        return "I don't have that information in the uploaded documents."

    return "Unknown tool"


class Agent:
    """
    Eurika AI Agent using OpenCode Zen GPT-5-nano.
    """

    def __init__(self):
        self.base_url = OPENCODE_ZEN_BASE_URL
        self.api_key = OPENCODE_ZEN_API_KEY
        self.model = OPENCODE_ZEN_MODEL_NAME
        print(
            f"LLM config: base_url={self.base_url}, api_key_loaded={bool(self.api_key)}, "
            f"api_key_mask={mask_api_key(self.api_key)}"
        )

    async def get_response(
        self,
        user_message: str,
        session_id: str,
        history: list[dict] = None
    ) -> dict:
        """
        Get complete (non-streaming) agent response with tool use support.

        Args:
            user_message: The user's message
            session_id: The session ID for knowledge base access
            history: Previous conversation history

        Returns:
            dict with keys: text, tool_calls (list of tool calls made), error
        """
        if history is None:
            history = []

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_message}
        ]

        result = {"text": "", "tool_calls": [], "error": None}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=120.0) as client:
                max_iterations = 5
                iteration = 0

                while iteration < max_iterations:
                    iteration += 1

                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "tools": TOOLS,
                        "tool_choice": "auto"
                    }

                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }

                    safe_headers = dict(headers)
                    safe_headers["Authorization"] = mask_api_key(safe_headers["Authorization"])

                    print(
                        f"LLM request iteration={iteration} model={self.model} messages={len(messages)}"
                    )
                    print(f"LLM outgoing headers: {safe_headers}")
                    print(f"LLM request URL: {self.base_url.rstrip('/')}/chat/completions")

                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload
                    )

                    if response.status_code != 200:
                        text = response.text
                        print(f"LLM API error: {response.status_code} response={text}")
                        result["error"] = f"API error: {response.status_code} - {text}"
                        return result

                    try:
                        response_data = response.json()
                    except json.JSONDecodeError as e:
                        text = response.text
                        print(f"LLM JSON parse error: {e} response={text}")
                        result["error"] = f"Invalid JSON from LLM: {e} - {text}"
                        return result

                    choice = response_data.get("choices", [{}])[0]
                    message = choice.get("message", {})

                    if not message:
                        print(f"LLM missing message object: {response_data}")
                        result["error"] = f"No message returned from LLM: {response_data}"
                        return result

                    tool_calls = message.get("tool_calls", [])
                    content = message.get("content", "")
                    result["text"] = content

                    if tool_calls:
                        for tc in tool_calls:
                            tool_name = tc.get("function", {}).get("name")
                            arguments_raw = tc.get("function", {}).get("arguments", "{}")
                            try:
                                tool_args = json.loads(arguments_raw)
                            except json.JSONDecodeError:
                                tool_args = {}

                            result["tool_calls"].append({
                                "name": tool_name,
                                "arguments": tool_args
                            })

                            tool_result = execute_tool(tool_name, tool_args, session_id)

                            messages.append({
                                "role": "assistant",
                                "content": content,
                                "tool_calls": tool_calls
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.get("id"),
                                "content": tool_result
                            })

                        # Continue loop to get the model's final answer after the tool result
                        continue

                    # No function call, we are finished
                    break

                return result

        except ImportError:
            result["error"] = "httpx not installed. Run: pip install httpx"
        except Exception as e:
            result["error"] = str(e)

        return result

    async def stream_response(
        self,
        user_message: str,
        session_id: str,
        history: list[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream agent response with tool use support.

        Yields:
            dict events with types:
            - text: streaming text token
            - tool_call: tool being called
            - tool_result: tool execution result
            - done: completion
            - error: error message
        """
        if history is None:
            history = []

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_message}
        ]

        # Build tool choice string for OpenCode Zen format
        tool_choice = "auto"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=120.0) as client:
                # First call - get initial response
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": TOOLS,
                        "tool_choice": tool_choice,
                        "stream": True
                    }
                )

                if response.status_code != 200:
                    error_text = response.text
                    yield {"type": "error", "message": f"API error: {response.status_code} - {error_text}"}
                    return

                # Process streaming response
                text_buffer = ""
                tool_calls = []

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            continue

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        delta = chunk.get("choices", [{}])[0].get("delta", {})

                        # Handle content/text
                        if delta.get("content"):
                            token = delta["content"]
                            text_buffer += token
                            yield {"type": "text", "content": token}

                        # Handle tool calls
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                if len(tool_calls) <= tc.get("index", 0):
                                    tool_calls.append({
                                        "id": None,
                                        "name": None,
                                        "arguments": ""
                                    })
                                idx = tc.get("index", 0)
                                if tc.get("id"):
                                    tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls[idx]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls[idx]["arguments"] += tc["function"]["arguments"]

                # Process tool calls if any
                if tool_calls:
                    for tc in tool_calls:
                        if tc["name"] and tc["id"]:
                            yield {"type": "tool_call", "name": tc["name"], "id": tc["id"]}

                            # Execute tool
                            try:
                                args = json.loads(tc["arguments"])
                            except json.JSONDecodeError:
                                args = {}

                            result = execute_tool(tc["name"], args, session_id)

                            yield {"type": "tool_result", "tool_call_id": tc["id"], "result": result}

                            # Add tool result to messages
                            messages.append({"role": "assistant", "content": text_buffer})
                            tool_calls_formatted = [{
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": tc["arguments"]
                                }
                            } for tc in tool_calls if tc["name"] and tc["id"]]
                            # Reconstruct assistant message with tool_calls
                            messages.append({
                                "role": "assistant",
                                "tool_calls": tool_calls_formatted
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result
                            })

                            # Make follow-up call without tools to get final response
                            response = await client.post(
                                f"{self.base_url}/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {self.api_key}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "model": self.model,
                                    "messages": messages,
                                    "stream": True
                                }
                            )

                            async for line in response.aiter_lines():
                                if not line.strip():
                                    continue
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        continue
                                    try:
                                        chunk = json.loads(data_str)
                                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                                        if delta.get("content"):
                                            token = delta["content"]
                                            yield {"type": "text", "content": token}
                                    except json.JSONDecodeError:
                                        continue

                yield {"type": "done"}

        except ImportError:
            yield {"type": "error", "message": "httpx not installed. Run: pip install httpx"}
        except Exception as e:
            yield {"type": "error", "message": str(e)}


# Global agent instance
_agent = None


def get_agent() -> Agent:
    """Get the global agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent