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
    template = """You are an assistant that helps foodies manage and track bars, restaurants, cafes, coffee shops and other establishments they encounter and want to remember. 

    The user will send you the name of an establishment. If the user fails to specify the city they're in, assume the user is in Budapest, Hungary. 

    The name provided by the user may not be entirely accurate. You are responsible for using the tools at your disposal to figure out the establishment the user is referring to.  

    Once you've identified the name, return is as the final answer.

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
    Final Answer: the final answer should be a string containing the name of the establishment

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

    print(response)


def get_location_id(search_query="mazel tov", category="restaurants", address="budapest"):

    # Set the endpoint URL with the updated key parameter and search query
    url = f"https://api.content.tripadvisor.com/api/v1/location/search?key={TRIPADVISOR_API_KEY}&searchQuery={search_query}&category={category}&address={address}&language=en"

    # Set the request headers
    headers = {"accept": "application/json"}

    # Send the request
    response = requests.get(url, headers=headers)

    # Extract the desired information from the first object in the 'data' list
    first_result = response.json()['data'][0]
    location_id = first_result['location_id']

    return location_id

def get_location_details(location_id: str) -> Dict:
    """
    Function to retrieve location details from Tripadvisor API.

    Parameters:
    location_id (str): location ID for the desired location.

    Returns:
    results (Dict): dictionary containing values for description, website,
        rating, phone, longitude, latitude, cuisines, category, opening hours, 
        and address string.
    """
    url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/details?key={TRIPADVISOR_API_KEY}&language=en&fields=description,website,rating,phone,longitude,latitude,cuisine,category,opening_hours,address_obj"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    # Extract required fields from data
    description = data['description']
    website = data['website']
    address_string = data['address_obj']['address_string']
    rating = data['rating']
    phone = data['phone']
    longitude = data['longitude']
    latitude = data['latitude']
    cuisines = [cuisine['name'] for cuisine in data['cuisine']]
    category = data['category']['localized_name']
    hours = data['hours']['weekday_text']
    
    # Assemble the results dictionary and return
    results = {
        "description": description,
        "address_string": address_string,
        "website": website,
        "rating": rating,
        "phone": phone,
        "longitude": longitude,
        "latitude": latitude,
        "cuisines": cuisines,
        "category": category,
        "hours": hours
    }
    
    print(results)
    return results

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