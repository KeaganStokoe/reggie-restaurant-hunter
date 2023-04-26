from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser  # noqa: E501
from langchain.prompts import BaseChatPromptTemplate
from langchain import SerpAPIWrapper, LLMChain
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish, HumanMessage
from langchain.chat_models import ChatOpenAI
import re
import json
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def add_establishment(user_input: str):
    # Define which tools the agent can use to answer user queries
    search = SerpAPIWrapper(serpapi_api_key=SERPAPI_API_KEY)

    tools = [
        Tool(
            name = "Search",
            func=search.run,
            description=f"""useful for when you need to retrieve information about a 
            bar, restaurant or coffee shop that you don't have knowledge of. 
            Useful if you have established the name of the restaurant and need to find 
            the address, phone number, or website."""  # noqa: F541
        ),
    ]

    # Set up the base template
    template = """You are MichellinGPT. You help the user keep track of bars, restaurants, cafes, coffee shops and any other establishments they encounter and want to try. 

    The user will send you the name of a restaurant, bar or coffee shop and the city they are in. If the user fails to provide a city, assume the user is in Budapest, Hungary. 

    The name provided by the user may not be entirely accurate. You will search using the name provided and attempt to locate the establishment. 

    If you find something similar, assume that it is the correct establishment. Do not ask the user for input. Assume that you are correct and proceeed.

    You have access to the following tools:

    {tools}

    Use the following format:

    Search: the name provided by the user
    Thought: you should always think about what to do
    Action: the action to take
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times and should repeat until you have all the required information)
    Thought: I now know the final answer
    Final Answer: the final answer should be provided in JSON format and should include the name, verbose one paragraph description, and cusisine.

    ---

    Begin! 

    User input: {input}
    {agent_scratchpad}"""  # noqa: E501

# Set up a prompt template
    class CustomPromptTemplate(BaseChatPromptTemplate):
        # The template to use
        template: str
        # The list of tools available
        tools: List[Tool]
        
        def format_messages(self, **kwargs) -> str:
            # Get the intermediate steps (AgentAction, Observation tuples)
            # Format them in a particular way
            intermediate_steps = kwargs.pop("intermediate_steps")
            thoughts = ""
            for action, observation in intermediate_steps:
                thoughts += action.log
                thoughts += f"\nObservation: {observation}\nThought: "
            # Set the agent_scratchpad variable to that value
            kwargs["agent_scratchpad"] = thoughts
            # Create a tools variable from the list of tools provided
            kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])  # noqa: E501
            # Create a list of tool names for the tools provided
            kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
            formatted = self.template.format(**kwargs)
            return [HumanMessage(content=formatted)]
        
    prompt = CustomPromptTemplate(
    template=template,
    tools=tools,
    # This omits the `agent_scratchpad`, `tools`, and `tool_names` variables because those are generated dynamically  # noqa: E501
    # This includes the `intermediate_steps` variable because that is needed
    input_variables=["input", "intermediate_steps"]
)

    class CustomOutputParser(AgentOutputParser):
        
        def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
            # Check if agent should finish
            if "Final Answer" in llm_output:
                return AgentFinish(
                    # Return value is a dictionary with a single `output` key
                    # It is not recommended to try anything else at the moment :)
                    return_values={"output": llm_output.split("Final Answer:")[-1].strip()},  # noqa: E501
                    log=llm_output,
                )
            # Parse out the action and action input
            regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
            match = re.search(regex, llm_output, re.DOTALL)
            if not match:
                raise ValueError(f"Could not parse LLM output: `{llm_output}`")
            action = match.group(1).strip()
            action_input = match.group(2)
            # Return the action and action input
            return AgentAction(tool=action, 
                               tool_input=action_input.strip(" ").strip('"'),
                               log=llm_output)

    output_parser = CustomOutputParser()

    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, 
                     openai_api_key=OPENAI_API_KEY)

    # LLM chain consisting of the LLM and a prompt
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    tool_names = [tool.name for tool in tools]
    agent = LLMSingleActionAgent(
    llm_chain=llm_chain, 
    output_parser=output_parser,
    stop=["\nObservation:"], 
    allowed_tools=tool_names
)

    agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, 
                                                        tools=tools, 
                                                        verbose=True)

    response = agent_executor.run(user_input)

    write_establishment_to_json_file(response)

def write_establishment_to_json_file(response):
    with open('stores.json', 'r') as f:
        data = json.load(f)

    # Parse the response string
    new_data = json.loads(response)

    # Convert all text to lowercase
    new_data = {key: value.lower() if isinstance(value, str) else value for key, 
                value in new_data.items()}

    # Append the new data to the existing data
    data.append(new_data)

    # Write the updated data back to stores.json
    with open('stores.json', 'w') as f:
        json.dump(data, f, indent=2)

    print('Data updated')