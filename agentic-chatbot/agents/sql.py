from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from agents.models import db, llm_4o_mini
from prompts.sql import SQL_AGENT_SYSTEM_MESSAGE

toolkit = SQLDatabaseToolkit(db=db, llm=llm_4o_mini)
tools = toolkit.get_tools()
state_modifier = SQL_AGENT_SYSTEM_MESSAGE.format(top_k=10)

sql_agent = create_react_agent(
    model=llm_4o_mini, tools=tools, state_modifier=state_modifier
)


@tool
def process_sql(question: str) -> str:
    """Use this tool to retrieve information from the PostgreSQL database.
    Args:
        question (str): The question to retrieve information from the database.
    Returns:
        str: The answer from the database.
    """
    print("TOOL: process_sql with question:", question)

    inputs = {"messages": [("user", question)]}
    final_answer = None

    for s in sql_agent.stream(
        inputs,
        stream_mode="values",
    ):
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print("DEBUG:", message)
        else:
            print("DEBUG:", message.content)
            final_answer = message.content

    return final_answer or "No answer found"
