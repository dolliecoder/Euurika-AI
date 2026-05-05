"""
Agent Module - OpenAI GPT with Tools for Eurika AI
Streaming agent with knowledge base search and TTS integration
"""

import os
import json
import asyncio
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from utils.knowledge_base import KnowledgeBase
from utils.tts import TextToSpeech


# System prompt for the voice assistant
SYSTEM_PROMPT = """You are Eurika, a helpful and friendly voice assistant.
You answer questions conversationally, as if speaking to someone in person.
Keep responses concise and natural - this is voice, not text chat.
Use the search_knowledge_base tool to find answers from uploaded documents.
If you can't find relevant information, be honest about it.
Never say things like "based on the document" - just answer naturally.
If a question is complex or the user seems frustrated, suggest escalating to a human.
Be warm, empathetic, and helpful."""


# Tool definitions for OpenAI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the uploaded FAQ documents to find answers",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information"
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
            "description": "Escalate the conversation to a human agent when the question is too complex, sensitive, or the user requests it",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why human escalation is needed"
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
            "description": "Log when a question couldn't be answered from the knowledge base",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question that couldn't be answered"
                    }
                },
                "required": ["question"]
            }
        }
    }
]


class VoiceAgent:
    """Streaming voice agent with tool use and TTS"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        tts: Optional[TextToSpeech] = None
    ):
        """Initialize the agent"""
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.kb = knowledge_base
        self.tts = tts
        self.model = "gpt-4o-mini"  # Fast, capable, good tool support
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: dict,
        session_id: str
    ) -> str:
        """Execute a tool and return the result"""
        if tool_name == "search_knowledge_base":
            query = tool_args.get("query", "")
            results = self.kb.search(session_id, query, top_k=3)
            if results:
                return "\n\n".join(results)
            return "No relevant information found in the documents."
        
        elif tool_name == "escalate_to_human":
            reason = tool_args.get("reason", "")
            print(f"Escalation requested: {reason}")
            return "I'll connect you with a human agent who can help with this. Please hold on."
        
        elif tool_name == "log_unanswered":
            question = tool_args.get("question", "")
            print(f"Unanswered question logged: {question}")
            return "Question logged for review."
        
        return "Unknown tool"
    
    async def run_streaming(
        self,
        transcript: str,
        session_id: str,
        ws,
        history: list[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Run the agent with streaming output
        
        Yields:
            dict: Message events (text, audio, tool calls, etc.)
        """
        messages = (history or []) + [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript}
        ]
        
        text_buffer = ""
        sentence_buffer = ""
        
        while True:
            # Streaming OpenAI call
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=True
            )
            
            tool_calls = []
            
            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # Handle text content
                if delta.content:
                    token = delta.content
                    text_buffer += token
                    sentence_buffer += token
                    
                    # Yield text token
                    yield {"type": "text", "content": token}
                    
                    # Stream TTS at sentence boundaries
                    if token in ".!?" and sentence_buffer.strip():
                        await self._stream_tts(sentence_buffer.strip(), ws)
                        sentence_buffer = ""
                
                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index >= len(tool_calls):
                            tool_calls.append({
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": ""
                            })
                        if tc.function.arguments:
                            tool_calls[len(tool_calls) - 1]["arguments"] += tc.function.arguments
            
            # Flush remaining text
            if sentence_buffer.strip():
                await self._stream_tts(sentence_buffer.strip(), ws)
            
            # Check if we have tool calls
            if not tool_calls:
                yield {"type": "done"}
                break
            
            # Execute tools
            tool_results = []
            for tc in tool_calls:
                yield {"type": "tool_call", "name": tc["name"], "arguments": tc["arguments"]}
                
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                
                result = await self.execute_tool(tc["name"], args, session_id)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })
                yield {"type": "tool_result", "name": tc["name"], "result": result}
            
            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": text_buffer})
            messages.extend(tool_results)
            text_buffer = ""
    
    async def _stream_tts(self, text: str, ws) -> None:
        """Stream TTS audio chunks to WebSocket"""
        if not self.tts or not text:
            return
        
        try:
            async for audio_chunk in self.tts.stream_audio(text):
                await ws.send_json({
                    "type": "audio_chunk",
                    "data": audio_chunk
                })
        except Exception as e:
            print(f"TTS stream error: {e}")


def get_agent(
    api_key: Optional[str] = None,
    knowledge_base: Optional[KnowledgeBase] = None,
    tts: Optional[TextToSpeech] = None
) -> VoiceAgent:
    """Factory function to get agent instance"""
    return VoiceAgent(
        api_key=api_key,
        knowledge_base=knowledge_base,
        tts=tts
    )
