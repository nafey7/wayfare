"""Shared prompt fragments used across multiple agent prompts.

Constants defined here are appended to agent system prompts to avoid
copy-pasting identical blocks across flight, hotel, itinerary, and
general agent prompts.
"""

# Temporarily disabled — suggestions feature not yet wired to frontend chips.
# Re-enable by uncommenting the block below.
# SUGGESTIONS_RULE = """
#
# ## Follow-up Suggestions
# At the very end of every response, provide exactly 3 short follow-up suggestions.
# Format on the LAST line: [SUGGESTIONS]suggestion one|suggestion two|suggestion three[/SUGGESTIONS]
# - Natural questions/prompts a user would type (not action labels)
# - **Match the current phase**: gathering info → suggest concrete clickable answers (city names, \
# dates, trip types, counts); after results → relevant next steps. \
# NEVER suggest post-result actions before any search/generation is done.
# - Keep each under 50 characters
# - Do NOT include this tag anywhere else in your response
# - NEVER suggest "book" actions — booking is via UI buttons, not chat"""

SUGGESTIONS_RULE = ""
