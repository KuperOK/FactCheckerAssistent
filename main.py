import os
import time
import streamlit as st
from openai import OpenAI
from datetime import datetime
from htmldate import find_date
# from serpapi import GoogleSearch
from serpapi.google_search import GoogleSearch

os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']

api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=api_key)

assistant_instructions_for_urls = """
    some instructions
    """

assistant_instructions_for_db = """
    some instructions
    """


def get_gpt_response(prompt, system_prompt, model="gpt-4o-mini", max_tokens=150, temperature=0.7):
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return completion.choices[0].message.content.strip()


def parse_to_google_query(user_input):
    system_prompt = ("""
        some system prompt
        """)

    return get_gpt_response(user_input, system_prompt)


os.environ['SEARCH_API_KEY'] = st.secrets['SEARCH_API_KEY']

search_api_key = os.getenv('SEARCH_API_KEY')

def google_search2(query):
    params = {
        "engine": "bing",
        "q": query,
        "api_key": search_api_key,
        "num": 10
    }
    #
    search = GoogleSearch(params)
    results = search.get_dict()


    if "organic_results" in results:
        return [result["link"] for result in results["organic_results"]]
    else:
        return []


def trim_edges(s):
    if len(s) <= 2:
        return ''
    return s[1:-1]


def get_db_search_result(user_input):
    assistant = client.beta.assistants.retrieve(assistant_id="asst_18BMFgE7nPtw0rXqHyNdSr6d")
    message_file1 = client.files.retrieve(file_id="file-dotZckOHgcmUg7PKK5lK9rIj")
    message_file2 = client.files.retrieve(file_id="file-aXhhBztJBIyie63U7EoM8eqT")

    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        instructions=assistant_instructions_for_db,
        model="gpt-4o-mini",
        temperature=0.7,
        tools=[{"type": "file_search"}]
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": user_input,
                "attachments": [
                    {"file_id": message_file1.id, "tools": [{"type": "file_search"}]},
                    {"file_id": message_file2.id, "tools": [{"type": "file_search"}]}
                ],
            }
        ]
    )

    run = run_assistant(assistant, thread)
    result = print_result(run, thread)
    return result


def get_gpt_analysis(user_input, url_date_dict):
    assistant = client.beta.assistants.retrieve(assistant_id="asst_18BMFgE7nPtw0rXqHyNdSr6d")

    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        instructions=assistant_instructions_for_urls,
        model="gpt-4o-mini",
        temperature=0.7
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": user_input + "some string " + str(url_date_dict)
            }
        ]
    )
    print("\n\n\n")
    print(user_input + "some user input" + str(url_date_dict))

    run = run_assistant(assistant, thread)
    result = print_result(run, thread)
    return result


def run_assistant(assistant, thread):
    return client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=assistant.id)


def print_result(run, thread):
    start_time = time.time()

    while time.time() - start_time < 20:
        messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

        if messages:
            message_content = messages[0].content[0].text
            annotations = message_content.annotations
            citations = []
            for index, annotation in enumerate(annotations):
                message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = client.files.retrieve(file_citation.file_id)
                    citations.append(f"[{index}] {cited_file.filename}")
            result = message_content.value + "\n" + "\n".join(citations)
            return result

        time.sleep(1)

    return "some message"


def find_publication_date(url):
    try:
        date = find_date(url)
        return date
    except Exception as e:
        return str(e)


def main(user_input):
    print("\n\n")
    # db_search_result = get_db_search_result(user_input)
    db_search_result = "message from db"

    if db_search_result.strip() == "Результатів не знайдено.":
        user_input += " some string" + str(datetime.now().date())
        google_query = parse_to_google_query(user_input)
        print("google_query: " + google_query)
        search_results = google_search2(google_query)

        if not search_results:
            st.write("some string")
            return

        url_date_dict = {url: find_publication_date(url) for url in search_results}

        analysis_result = get_gpt_analysis(user_input, url_date_dict)
        st.write(analysis_result)
        print(analysis_result)
    else:
        st.write(db_search_result)
        print(db_search_result)
        print("els")


# Streamlit UI
st.title('Fact-Checking Assistant')
st.write("Enter your query and get verified information:")
user_input = st.text_input("Your query:")

if st.button('Submit'):
    if user_input:
        main(user_input)
    else:
        st.write("Please enter a query.")
