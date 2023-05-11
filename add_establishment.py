from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser  # noqa: E501
from langchain.prompts import BaseChatPromptTemplate
from langchain import SerpAPIWrapper, LLMChain
from typing import List, Union, Dict
from langchain.schema import AgentAction, AgentFinish, HumanMessage
from langchain.chat_models import ChatOpenAI
import re
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TRIPADVISOR_API_KEY = os.getenv("TRIPADVISOR_API_KEY")

def get_location_name(user_input: str):

    # Define which tools the agent can use to answer user queries
    search = SerpAPIWrapper(serpapi_api_key=SERPAPI_API_KEY)

    tools = [
        Tool(
            name = "Search",
            func=search.run,
            description=f"""useful for when you need to retrieve the name of a location
              (restaurant, bar, coffee shop, cafe)"""  # noqa: F541
        ),
    ]

    # Set up the base template
    template = """You're given the name of a restaurant by a user. It may be correct, but it will most likely contain a few errors. 

    Use the tools at your disposal to determine the name of the restaurant the user is referring to. If you are reasonably confident, proceed to providing the answer.

    {tools}

    Use the following format:

    Search: the name provided by the user
    Thought: you should always think about what to do
    Action: the action to take
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat 3 times or until you have all the required information, whichever comes sooner)
    Thought: I now know the final answer
    Final Answer: the final answer should be the name of the establishment, with no additional information

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
            if ("Final Answer") in llm_output:
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

    return response

def get_location_id(search_query, category="restaurants", address="budapest"):  # noqa: E501

    # Set the endpoint URL with the updated key parameter and search query
    url = f"https://api.content.tripadvisor.com/api/v1/location/search?key={TRIPADVISOR_API_KEY}&searchQuery={search_query}&category={category}&address={address}&language=en"  # noqa: E501

    # Set the request headers
    headers = {"accept": "application/json"}

    # Send the request
    response = requests.get(url, headers=headers)

# Check if response is not empty before extracting the data
    if response.status_code != 200 or "data" not in response.json():
        return None

	# Extract the desired information from the first object in the 'data' list
    try:
        first_result = response.json()['data'][0]
        location_id = first_result['location_id']
    except (KeyError, IndexError):
        return ''

    return location_id

def get_location_details(location_id: str) -> Dict:
    """
    Function to retrieve location details from Tripadvisor API.

    Parameters:
    location_id (str): location ID for the desired location.

    Returns:
    results (Dict): dictionary containing values for name, description,
        address_string, website, rating, phone, longitude, latitude, cuisines,
        category, and hours.
    """
    url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/details?key={TRIPADVISOR_API_KEY}&language=en&fields=name,description,website,rating,phone,longitude,latitude,cuisine,category,hours,address_obj"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    data = response.json()

    # Extract required fields from data
    results = {"name": data.get("name"),
               "description": data.get("description"),
               "address_string": data.get("address_obj", {}).get("address_string"),
               "website": data.get("website"),
               "rating": data.get("rating"),
               "phone": data.get("phone"),
               "longitude": data.get("longitude"),
               "latitude": data.get("latitude"),
               "cuisines": [cuisine.get("name") for cuisine in data.get("cuisine", [])],
               "category": data.get("category", {}).get("localized_name"),
               "hours": data.get("hours", {}).get("weekday_text")}

    return results 

def write_establishment_to_json_file(new_data: Dict):
    # Convert all text in the new data to lowercase
    new_data = {key: value.lower() if isinstance(value, str) else value for key, 
                value in new_data.items()}

    # Load existing data (if any)
    try:
        with open('stores.json', 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # If the file doesn't exist yet, start with an empty list
        data = []

    # Append the new item to the list
    data.append(new_data)

    # Write the updated data (with indentation)
    with open('stores.json', 'w') as f:
        json.dump(data, f, indent=2)

    print('Data successfully updated')

def add_location(user_input:str):
    name = get_location_name(user_input)
    print(f"Name retrieved - {name}")
    location_id = get_location_id(search_query=name)
    print(f"ID retrieved - {location_id}")
    location_details = get_location_details(location_id)
    print("Details retrieved")
    write_establishment_to_json_file(location_details)
    return True