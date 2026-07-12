"""Agent prompt service for managing AI agent prompts."""

import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_connection

from .schemas import AgentPromptCreate, AgentPromptResponse, AgentPromptUpdate

logger = logging.getLogger(__name__)


# Default prompts for each agent(module-level constant)
DEFAULT_PROMPTS: dict[str, Any] = {
    "intent_recognizer": {
        "goal": "Classifies user messages into predefined intents (BOOK_FLIGHT, VIEW_BOOKINGS, etc.) using Gemini AI with pattern-matching fallback",
        "prompt_template": """Analyze this user message and determine their intent:
Message: "{message}"

Previous context: {context}

Classify the intent as ONE of:

1. CREATE_ITINERARY (highest priority - trip planning):
   - User wants to PLAN a trip, create itinerary, or get travel suggestions
   - Keywords: "plan", "planning", "itinerary", "organize trip", "help me plan", "create itinerary", "make itinerary"
   - Mentions trip DURATION: "for 7 days", "3-day trip", "a week", "10 days"
   - Asks for trip suggestions: "what should I do in", "help me with my vacation"
   - Examples:
     ✓ "Plan my trip to Paris for 5 days"
     ✓ "I'm planning a vacation to Rome"
     ✓ "Create an itinerary for London"
     ✓ "Help me plan a 7-day trip to Barcelona"
     ✓ "I want to visit Paris for a week" (duration = planning intent)
     ✓ "Planning a trip to Tokyo in March"

   RULE: If "plan", "planning", or duration is mentioned → CREATE_ITINERARY (even if dates/destination present)

2. BOOK_FLIGHT (direct flight booking only):
   - User wants to BOOK or SEARCH for specific flights
   - Must have explicit booking/search intent WITHOUT planning keywords
   - Keywords: "book flight", "search flights", "find flights", "need a flight", "fly to" (only if no planning context)
   - Examples:
     ✓ "Book me a flight to Paris on June 15"
     ✓ "Search flights from London to New York on March 20"
     ✓ "I need a flight to Barcelona next week"
     ✓ "Find me flights to Rome leaving tomorrow"
     ✗ "I want to visit Paris for a week" → CREATE_ITINERARY (duration mentioned)
     ✗ "Planning to fly to Rome in June" → CREATE_ITINERARY ("planning" keyword)

3. BOOK_HOTEL:
   - User wants to book accommodation
   - Keywords: "book hotel", "find hotel", "need accommodation", "place to stay"
   - Examples:
     ✓ "Book a hotel in Paris"
     ✓ "Find me accommodation in London"

4. BOOK_ACTIVITY:
   - User wants to book activities or tours
   - Keywords: "book tour", "activities", "things to do", "excursion"

5. VIEW_BOOKINGS:
   - User wants to see existing bookings
   - Keywords: "my bookings", "my trips", "show my reservations"

6. GENERAL_QUERY:
   - General travel questions or chat
   - Examples: "What's the weather like?", "Hello", "Tell me about Paris"

7. UNKNOWN:
   - Cannot determine intent

DECISION PRIORITY (apply in this order):
1. If "plan", "planning", "itinerary", or trip duration → CREATE_ITINERARY
2. If explicit "book flight", "search flights" WITHOUT planning keywords → BOOK_FLIGHT
3. If "book hotel" → BOOK_HOTEL
4. Otherwise → GENERAL_QUERY or UNKNOWN

Also provide a confidence score (0.0 to 1.0):
- 0.9-1.0: Very clear intent with strong keywords
- 0.7-0.8: Clear intent with moderate keywords
- 0.5-0.6: Weak signals, uncertain
- 0.0-0.4: Very unclear, default to GENERAL_QUERY

Return ONLY in this format:
INTENT: <intent>
CONFIDENCE: <score>""",
    },
    "data_extractor": {
        "goal": "Extracts structured flight booking data (origin, destination, dates, passengers) from natural language messages using Gemini AI with validation",
        "prompt_template": """Extract flight booking information from this message.
Message: "{message}"

Current context: {context}
Today's date: {today_date}
{context_instruction}

Extract ALL of the following that are mentioned:
- origin: departure city or airport code
- destination: arrival city or airport code
- departure_date: departure date (ISO format YYYY-MM-DD)
- return_date: return date if mentioned (ISO format or null)
- trip_type: "one_way" or "round_trip"
- adults: number of adult passengers (default 1)
- children: number of children (default 0)
- infants: number of infants (default 0)
- child_ages: list of children ages if mentioned
- cabin_class: economy/premium_economy/business/first (default economy)
- direct_only: true if user wants only direct flights
- airline_preference: specific airline if mentioned
- checked_bags: number of checked bags
- departure_time_preference: morning/afternoon/evening if mentioned

Return ONLY valid JSON. If a field is not mentioned, omit it from the response.
Example: {{"origin": "Amsterdam", "destination": "Paris", "departure_date": "2024-03-15"}}""",
    },
    "general_travel_handler": {
        "goal": "Generates conversational AI responses for non-flight travel queries using the 'MyVoya' personality via Gemini AI",
        "prompt_template": """You are MyVoya, an enthusiastic travel assistant! You're super excited about helping people travel.

CRITICAL RULES:
1. NEVER list what information you need (no bullet points of required fields)
2. Keep responses SHORT - max 1-2 sentences
3. Be enthusiastic and excited about their destination
4. Ask ONE specific question at a time (like "Where would you like to go to?")
5. Don't mention your capabilities or what's coming soon

{specific_context}

User message: "{message}"

Give a SHORT, enthusiastic response and ask ONE specific question.""",
    },
}


class AgentPromptService:
    """Service for managing AI agent prompts"""

    def _get_collection(self) -> AsyncIOMotorCollection[Any]:
        """Get the agent_prompts collection"""
        return get_connection().get_collection("agent_prompts")

    async def get_all_prompts(self) -> list[AgentPromptResponse]:
        """Get all agent prompts"""
        collection = self._get_collection()
        cursor = collection.find({})
        prompts = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            prompts.append(AgentPromptResponse.model_validate(doc))
        return prompts

    async def get_prompt_by_agent(self, agent_name: str) -> AgentPromptResponse | None:
        """Get prompt for specific agent"""
        collection = self._get_collection()
        doc = await collection.find_one({"agent_name": agent_name, "is_active": True})
        if doc:
            doc["id"] = str(doc.pop("_id", ""))
            return AgentPromptResponse.model_validate(doc)
        return None

    async def get_prompt_template(self, agent_name: str) -> str:
        """Get the prompt template for an agent, with fallback to default"""
        prompt = await self.get_prompt_by_agent(agent_name)
        if prompt:
            return prompt.prompt_template

        # Fallback to default prompt
        default = DEFAULT_PROMPTS.get(agent_name)
        if default:
            logger.warning(f"Using default prompt for agent: {agent_name}")
            return default["prompt_template"]

        logger.error(f"No prompt found for agent: {agent_name}")
        return "You are a helpful AI assistant."

    async def create_prompt(
        self, prompt_data: AgentPromptCreate, user_id: str | None = None
    ) -> AgentPromptResponse:
        """Create a new agent prompt"""
        collection = self._get_collection()

        # Deactivate existing prompts for this agent
        await collection.update_many(
            {"agent_name": prompt_data.agent_name},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )

        # Create new prompt
        prompt_dict = prompt_data.model_dump()
        prompt_dict.update(
            {
                "created_by": user_id,
                "updated_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        result = await collection.insert_one(prompt_dict)
        prompt_dict["id"] = str(result.inserted_id)
        logger.info(f"Created new prompt for agent: {prompt_data.agent_name}")
        return AgentPromptResponse.model_validate(prompt_dict)

    async def update_prompt(
        self,
        agent_name: str,
        prompt_data: AgentPromptUpdate,
        user_id: str | None = None,
    ) -> AgentPromptResponse | None:
        """Update an agent prompt"""
        collection = self._get_collection()

        update_data = {
            k: v for k, v in prompt_data.model_dump().items() if v is not None
        }
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = user_id

        result = await collection.find_one_and_update(
            {"agent_name": agent_name, "is_active": True},
            {"$set": update_data},
            return_document=True,
        )

        if result:
            result["id"] = str(result.pop("_id", ""))
            logger.info(f"Updated prompt for agent: {agent_name}")
            return AgentPromptResponse.model_validate(result)

        return None

    async def initialize_default_prompts(self) -> None:
        """Initialize default prompts if they don't exist"""
        for agent_name, default_data in DEFAULT_PROMPTS.items():
            existing = await self.get_prompt_by_agent(agent_name)
            if not existing:
                prompt_data = AgentPromptCreate(
                    agent_name=agent_name,
                    goal=default_data["goal"],
                    prompt_template=default_data["prompt_template"],
                )
                await self.create_prompt(prompt_data)
                logger.info(f"Initialized default prompt for agent: {agent_name}")


# Singleton instance
agent_prompt_service = AgentPromptService()
