import os
import requests
import json
import tiktoken
from openai import AzureOpenAI
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv


#environment variabelen van .env laden
load_dotenv()

#azure cognitive search credentials (erasmus search service / upbeat pump)
SEARCH_SERVICE_NAME = os.getenv('SEARCH_SERVICE_NAME')
SEARCH_INDEX_NAME = os.getenv('SEARCH_INDEX_NAME')
SEARCH_API_KEY = os.getenv('SEARCH_API_KEY')

#azure OpenAI credentials (https://deerasmusbot.openai.azure.com/)
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_MODEL = os.getenv('AZURE_OPENAI_MODEL')
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_MODEL,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

deployment_name = 'gpt-35-turbo'

#geïndexte data opzoeken
def search_index(query):
    endpoint = f"https://{SEARCH_SERVICE_NAME}.search.windows.net"
    api_version = '2021-04-30-Preview'
    search_url = f"{endpoint}/indexes/{SEARCH_INDEX_NAME}/docs/search?api-version={api_version}"
    headers = {
        'Content-Type': 'application/json',
        'api-key': SEARCH_API_KEY
    }

    search_payload = {
        "search": query,
        "queryType": "full"
    }
    response = requests.post(search_url, headers=headers, json=search_payload)
    results = response.json()
    return results

#tokens optellen
def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

#response genereren met OpenAI
def generate_response(index_results, user_query, max_tokens=8192):
    # content van de documenten combineren
    context = "\n".join([doc['content'] for doc in index_results['value']])
    
    # tellen hoeveel tokens er overblijven voor de context
    user_query_tokens = count_tokens(user_query)
    max_context_tokens = max_tokens - user_query_tokens - 200 #200 als buffer 
    
    # context afkappen als de context token limiet overschreden is
    context_tokens = count_tokens(context)
    if context_tokens > max_context_tokens:
        truncated_context = ""
        current_tokens = 0
        for token in context.split():
            current_tokens += count_tokens(token)
            if current_tokens > max_context_tokens:
                break
            truncated_context += token + " "
        truncated_context = truncated_context.strip()
    else:
        truncated_context = context
    
    prompt = f"Context: {truncated_context}\nUser: {user_query}\nAI:"

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            #Systeem rol zeggen dat die een chatbot voor de school is
            {"role": "system", "content": "You are an assistant that only responds to questions related to the ErasmusHogeschool Brussel, and you only use the data that is given to you. Whenever you receive questions unrelated to the school, ignore the content of the question and say that you are a chatbot for Erasmus Hogeschool Brussel and can only assist with questions relating this school."},
            {"role": "user", "content": user_query},
            {"role": "system", "content": truncated_context}
        ]
    )

    return response.choices[0].message.content

# Functie om de relevantie van de vraag the checken
def handle_query(user_query):
    index_results = search_index(user_query)
    ai_response = generate_response(index_results, user_query)
    return ai_response

    # Check if the search results contain relevant information
    # if 'value' in index_results and index_results['value']:
    #     # Check for relevance keywords
    #     relevant_keywords = ["Erasmushogeschool", "Brussel", "Applied Computer Science", "Business IT", "Networks & Security", "Intelligent Robotics", "Software Engineering", "Erasmus University College"]
    #     context = "\n".join([doc['content'] for doc in index_results['value']])
    #     if any(keyword.lower() in context.lower() for keyword in relevant_keywords):
    #         ai_response = generate_response(index_results, user_query)
    #         return ai_response
    #     else:
    #         return "I'm sorry but I can only answer questions related to Erasmushogeschool Brussel and its courses. Please ask a question related to the school."
    # else:
    #     return "I'm sorry but I can only answer questions related to Erasmushogeschool Brussel and its courses. Please ask a question related to the school."


# Flask app voor de frontend
app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_query = data.get('query')
    response = handle_query(user_query)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)