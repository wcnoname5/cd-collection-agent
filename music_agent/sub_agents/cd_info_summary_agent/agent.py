from google.adk import Agent

from . import prompt

MODEL = "gemini-2.5-pro"

cd_summary_agent = Agent(
    model=MODEL,
    name="cd_summary_agent",
    instruction=prompt.CD_INFORMATION_SUMMARY_PROMPT,
)
