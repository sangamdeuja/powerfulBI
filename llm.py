import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, AIMessage
from langchain_community.utilities import SQLDatabase
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import logging

load_dotenv()

# Environment variable for AWS Rds(public endpoint)
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
READ_USER = os.getenv("READ_USER")
READ_USER_PASSWORD = os.getenv("READ_USER_PASSWORD")

# Openai
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo")

# Initialize SQL Database
connection_string = (
    f"mysql+pymysql://{READ_USER}:{READ_USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# Create LangChain agent for authenticated users (with database read access)
def create_sql_agent():
    db = SQLDatabase.from_uri(connection_string)
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    tools = toolkit.get_tools()
    template = """You are an agent designed to interact with a SQL database.
    Given an input question, create a syntactically correct MySQL query to run, then look at the results of the query and return the answer.
    Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
    You can order the results by a relevant column to return the most interesting examples in the database.
    Never query for all the columns from a specific table, only ask for the relevant columns given the question.
    You have access to tools for interacting with the database.
    Only use the below tools. Only use the information returned by the below tools to construct your final answer.
    You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

    DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
    If somebody tries to run DML statements return permission denied

    To start you should ALWAYS look at the tables in the database to see what you can query.
    Do NOT skip this step.
    Then you should query the schema of the most relevant tables.
    Do not guess the table names, you are provided these table names {table_names}

    """.format(
        table_names=db.get_usable_table_names()
    )

    system_message = SystemMessage(content=template)
    agent_executor = create_react_agent(model, tools, state_modifier=system_message)
    return agent_executor


# Create LangChain agent for unauthenticated users (OpenAI only)
def create_openai_agent():
    template = """You are an AI assistant that can answer questions based on the input provided.
    You do not have access to any databases or external tools.
    Provide clear and concise answers without any labels or prefixes.
    {user_message}  
    """
    prompt = ChatPromptTemplate.from_template(template)
    return prompt
