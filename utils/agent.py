import json
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
import dotenv

dotenv.load_dotenv()

# We use gpt-4o-mini which is fast/efficient since gpt-5-nano does not exist officially.
MODEL_NAME = "gpt-4o-mini"

SYSTEM_PROMPT = """You are Eurika AI, an elegant and helpful voice assistant for a company.
Answer questions using ONLY the search_knowledge_base tool.
If you cannot find a relevant answer after searching, use log_unanswered.
If the question is complex or the user seems frustrated, use escalate_to_human.
Keep answers concise and conversational — this is voice, not text.
Never say 'based on the document' — just answer naturally.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the uploaded document to answer the user's question",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Use when the question is too complex or sensitive",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_unanswered",
            "description": "Use when no relevant answer found in knowledge base",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"}
                },
                "required": ["question"]
            }
        }
    }
]

client = AsyncOpenAI()

def execute_tool(tool_name: str, args: dict, session_id: str, chroma_client) -> str:
    """Execute the chosen tool synchronously (or wrap in async if needed)"""
    if tool_name == "search_knowledge_base":
        try:
            collection = chroma_client.get_collection(name=session_id)
            results = collection.query(
                query_texts=[args.get("query", "")],
                n_results=3
            )
            docs = results.get("documents", [])
            if docs and docs[0]:
                return "\n\n".join(docs[0])
            return "No information found in documents."
        except Exception as e:
            logging.error(f"Search failed: {e}")
            return "Failed to search the documents."
            
    elif tool_name == "escalate_to_human":
        logging.info(f"ESCALATION: {args.get('reason')}")
        return "escalation_logged"
        
    elif tool_name == "log_unanswered":
        logging.info(f"UNANSWERED: {args.get('question')}")
        return "logged"
    
    return "unknown_tool"

from utils.tts import stream_tts_chunk

async def run_agent(transcript: str, session_id: str, chroma_client, history: list, ws) -> str:
    """
    Run the agent, execute tools if required, and stream text and audio via WebSocket.
    Returns the updated assistant content.
    """
    messages = history + [{"role": "user", "content": transcript}]
    
    full_response = ""
    
    while True:
        # Create stream
        stream = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
            stream=True
        )
        
        tool_calls = {}
        chunk_text = ""
        text_buffer = ""
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # 1. Handle text streaming
            if delta.content:
                text = delta.content
                chunk_text += text
                full_response += text
                text_buffer += text
                
                await ws.send_json({"type": "agent_text", "text": text})
                
                # Check for sentence boundaries to trigger TTS
                if any(punct in text for punct in ".!?\n"):
                    await stream_tts_chunk(text_buffer, ws)
                    text_buffer = ""
                
            # 2. Handle tool calls streaming
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls:
                        tool_calls[tc.index] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                    if tc.function.arguments:
                        tool_calls[tc.index]["arguments"] += tc.function.arguments

        # If there are no tool calls, we're done here
        if not tool_calls:
            if text_buffer.strip():
                await stream_tts_chunk(text_buffer, ws)
            await ws.send_json({"type": "agent_done"})
            break
            
        # Add the assistant message with tool calls to history
        assistant_message = {
            "role": "assistant", 
            "content": chunk_text or None,
            "tool_calls": [
                {
                    "id": tc["id"], 
                    "type": "function", 
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}
                } for tc in tool_calls.values()
            ]
        }
        messages.append(assistant_message)
        
        # Execute tools
        for index, tc in tool_calls.items():
            tool_name = tc["name"]
            try:
                args = json.loads(tc["arguments"])
            except json.JSONDecodeError:
                args = {}
                
            await ws.send_json({"type": "tool_call", "name": tool_name})
            tool_result = execute_tool(tool_name, args, session_id, chroma_client)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result
            })
            
        # Loop continues to send tool results back to completion
        
    return full_response
