from dotenv import load_dotenv
from openai import AzureOpenAI
import os
from src.website import read_website 
import json

load_dotenv()  # Load environment variables from .env file

# Set up your client with environment variables
MAX_COOKIE_SIZE = int(os.getenv('MAX_COOKIE_SIZE', 4000))  # Default to 4000 if not set
api_key = os.getenv('AZURE_OPENAI_API_KEY')
endpoint = os.getenv('ENDPOINT')
version = os.getenv('VERSION')
deployment = os.getenv('DEPLOYMENT_4o_mini')

client = AzureOpenAI(
    azure_endpoint=endpoint, 
    api_key=api_key,
    api_version=version
)


read_website_function = {
    "name": "read_website",
    "description": "Get the content of the website by its link. Call this whenever you need to read link content, for example when a customer provides a link to a job posting.",
    "parameters": {
        "type": "object",
        "properties": {
            "link": {
                "type": "string",
                "description": "The link to the website you want to read. For example: https://www.example.com/job/software-engineer",
            },
        },
        "required": ["link"],
        "additionalProperties": False
    }
}

def read_text_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except Exception as e:
        return f"Error reading text file: {e}"


# The system prompt for job postings
job_posting_system_prompt = read_text_file("job_posting_system_prompt.txt")


def call_tool(reply, messages): 
    tool_responses = []
    messages.append(reply)

    for tool_call in reply.tool_calls:
        if tool_call.function.name == "read_website":
            try:
                arguments = json.loads(tool_call.function.arguments)
                link = arguments.get('link')
                print(link)
                # Validate the link
                if not link or not link.startswith("http"):
                    raise ValueError(f"Invalid link: {link}")
                
                website_text = read_website(link)
                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": website_text
                })
            except Exception as e:
                # Handle errors gracefully
                error_message = f"Error processing tool_call_id {tool_call.id}: {e}"
                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": error_message
                })

        else:
            error_message = f"Error processing tool_call_id {tool_call.id}: Unsupported function {tool_call.function.name}"
            tool_responses.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": error_message
            })

    messages.extend(tool_responses)
    followup = client.chat.completions.create(
        model=deployment,
        messages=messages
    )

    return followup.choices[0].message.content



# Your existing chat function (with any imports it needs)
def chat(message, history):
    messages = [{"role": "system", "content": job_posting_system_prompt}] + history + [{"role": "user", "content": message}]
    print(messages)
    response = client.chat.completions.create(model=deployment, 
                                              messages=messages, tools = [{"type": "function", "function": read_website_function}])
    print(response)
    if response.choices[0].finish_reason=="tool_calls":
        message = response.choices[0].message
        response = call_tool(message, messages)
        response = client.chat.completions.create(model=deployment, messages=messages)
    
    return response.choices[0].message.content


def get_cookie_size_info(history):
    history_json = json.dumps(history)
    return {
        'size': len(history_json),
        'max_size': MAX_COOKIE_SIZE,
        'percentage': (len(history_json) / MAX_COOKIE_SIZE) * 100,
        'entries_count': len(history)
    }