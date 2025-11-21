
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .tools.add_cd_to_sheets_tool import add_cd_to_sheets_long_running, resume_add_cd_to_sheets
from .tools.check_collection_for_cd_tool import check_collection_for_cd

MODEL = "gemini-2.5-flash" # "gemini-2.5-pro"


add_cd_to_sheets_tool = LongRunningFunctionTool(
    func=add_cd_to_sheets_long_running,
    # name="add_cd_to_sheets",
    description="Search Discogs and add a CD to Google Sheets with human approval."
)

resume_add_cd_to_sheets_tool = LongRunningFunctionTool(
    func=resume_add_cd_to_sheets,
    # name="resume_add_cd_to_sheets",
    description="Resume the pending add-CD operation."
)


cd_agent = LlmAgent(
    name='cd_agent',
    model=MODEL,
    description=(
        "Search CD information via web search and manage CD metadata "
        "Help create and maintain a CD collection "
        "Managing CD collection metadata via Discogs and Google Sheets."
        "Provide music recommendations from CD collection."
     ),
    instruction=prompt.CD_COORDINATOR_PROMPT,
    output_key="target_cd",
    tools=[
        # TODO
        AgentTool(agent="cd_websearch_agent"),
        # add_cd_to_sheets_tool,
        # resume_add_cd_to_sheets_tool,
        # check_collection_for_cd()
    ]
)

root_agent = cd_agent
