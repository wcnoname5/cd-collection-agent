from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools import LongRunningFunctionTool
from tools.add_cd_to_sheets_tool import add_cd_to_sheets_long_running, resume_add_cd_to_sheets
from tools.check_collection_for_cd_tool import check_collection_for_cd

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
    model='gemini-2.5-flash',
    description='An agent for managing CD metadata via Discogs and Google Sheets.',
    instruction=(
        "You are a CD collection assistant. "
        "You can search Discogs, add CD metadata into Google Sheets, "
        "and check whether an album is already in the collection. "
        "Use tools when needed."
    ),
    tools=[
        add_cd_to_sheets_tool,
        resume_add_cd_to_sheets_tool,
        check_collection_for_cd()
    ]
)

root_agent = cd_agent
