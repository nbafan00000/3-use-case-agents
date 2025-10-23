from flask import Flask, request, jsonify, render_template, session
from flask import Response, stream_with_context
from openai import OpenAI
import os, base64
from dotenv import load_dotenv
import time
from datetime import date
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import json
import httpx

load_dotenv()
app = Flask(__name__)
app.secret_key = 'super_secret_key'  # For session

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

AGENT_IDS = {
    '1': 'asst_QLzsCtwgJDzcPWTf4FVpVt8q',  # Replace with actual
    '2': 'asst_8onKwY0XOHcshizOLuEGgOHU',
    '3': 'asst_43nQoLPoAIk3p8CV7D2zauId'
}

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

def get_credentials():
    creds = None

    # 1️⃣ Try to load token from Render environment variable (secure, headless)
    token_b64 = os.environ.get('TOKEN_PICKLE_B64')
    if token_b64:
        creds = pickle.load(io.BytesIO(base64.b64decode(token_b64)))

    # 2️⃣ Fallback: load local token.pickle (for local development)
    elif os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token_file:
            creds = pickle.load(token_file)

    # 3️⃣ If no valid credentials, refresh or generate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # Headless Render environment uses console-based flow
            if os.environ.get('RENDER') == "1":
                creds = flow.run_console()
            else:
                # Local development uses browser flow
                creds = flow.run_local_server(port=0)

        # Save token locally for future local runs
        with open('token.pickle', 'wb') as token_file:
            pickle.dump(creds, token_file)

    return creds
# def get_credentials():
#     creds = None
#     if os.path.exists('token.pickle'):
#         with open('token.pickle', 'rb') as token:
#             creds = pickle.load(token)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open('token.pickle', 'wb') as token:
#             pickle.dump(creds, token)
#     return creds

creds = get_credentials()
drive_service = build('drive', 'v3', credentials=creds)
docs_service = build('docs', 'v1', credentials=creds)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_agent', methods=['POST'])
def select_agent():
    agent_type = str(request.json['type'])
    thread = client.beta.threads.create()
    session['thread_id'] = thread.id
    session['agent_id'] = AGENT_IDS[agent_type]
    session['hand_off_json'] = {}  # For hand-offs
    return jsonify({'thread_id': thread.id, 'agent_id': AGENT_IDS[agent_type]})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = session.get('thread_id')
    agent_id = session.get('agent_id')
    client.beta.threads.messages.create(thread_id=thread_id, role='user', content=data['message'])
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=agent_id)
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            response = messages.data[0].content[0].text.value
            # If end of agent, parse JSON for hand-off
            if "structured JSON form" in response:  # Simple check; improve as needed
                try:
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    output_json = json.loads(response[json_start:json_end])
                    session['hand_off_json'] = output_json
                except:
                    pass
            break
        time.sleep(1)
    return response
# def chat():
#     data = request.json
#     thread_id = session.get('thread_id')
#     agent_id = session.get('agent_id')
#     if not thread_id or not agent_id:
#         return jsonify({'error': 'Please start an agent first before chatting.'}), 400

#     # Add user message
#     client.beta.threads.messages.create(thread_id=thread_id, role='user', content=data['message'])

#     # Create run
#     run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=agent_id)

#     def generate():
#         last_content = ''
#         while True:
#             run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
#             if run_status.status == 'completed':
#                 messages = client.beta.threads.messages.list(thread_id=thread_id, order='asc')
#                 assistant_messages = [msg for msg in messages.data if msg.role == 'assistant']
#                 if assistant_messages:
#                     current_content = assistant_messages[-1].content[0].text.value
#                     # Yield only new content (incremental diff)
#                     new_content = current_content[len(last_content):]
#                     if new_content:
#                         yield f"data: {new_content}\n\n"
#                     last_content = current_content
#                 yield "data: [DONE]\n\n"
#                 break
#             elif run_status.status in ['failed', 'cancelled', 'expired']:
#                 yield f"data: Error: Run {run_status.status}\n\n"
#                 break
#             time.sleep(0.5)  # Poll interval; adjust to 0.2 for faster if needed

#     return Response(stream_with_context(generate()), mimetype='text/event-stream')
# def chat():
#     data = request.json
#     thread_id = session.get('thread_id')
#     agent_id = session.get('agent_id')
#     if not thread_id or not agent_id:
#         return jsonify({'error': 'Please start an agent first before chatting.'}), 400

#     # Add user message
#     client.beta.threads.messages.create(thread_id=thread_id, role='user', content=data['message'])

#     # Create run and store its ID in session for streaming
#     run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=agent_id)
#     session['run_id'] = run.id

#     return jsonify({'status': 'Stream started'})


@app.route('/stream', methods=['GET'])
def stream():
    thread_id = session.get('thread_id')
    run_id = session.get('run_id')
    if not thread_id or not run_id:
        return jsonify({'error': 'No active run to stream.'}), 400

    def generate():
        last_content = ""
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run_status.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread_id, order='asc')
                assistant_messages = [msg for msg in messages.data if msg.role == 'assistant']
                if assistant_messages:
                    full_response = assistant_messages[-1].content[0].text.value
                    new_chunk = full_response[len(last_content):]  # Only new part for incremental
                    if new_chunk:
                        yield f"data: {new_chunk}\n\n"
                    last_content = full_response
                yield "data: [DONE]\n\n"
                break
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                yield f"data: Error: Run {run_status.status}\n\n"
                break
            time.sleep(0.5)  # Poll every 0.5 seconds

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file.save(file.filename)
    openai_file = client.files.create(file=open(file.filename, "rb"), purpose="assistants")
    thread_id = session.get('thread_id')
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Pre-populate fields from uploaded document.",
        attachments=[{"file_id": openai_file.id, "tools": [{"type": "file_search"}]}]
    )
    # Trigger run (similar to chat)
    agent_id = session.get('agent_id')
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=agent_id)
    # Poll as above...
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            response = messages.data[0].content[0].text.value
            break
        time.sleep(1)
    os.remove(file.filename)  # Clean up
    return jsonify({'response': response, 'status': 'File processed'})

@app.route('/complete', methods=['POST'])
def complete():
    final_data = session.get('hand_off_json', {})
    if not final_data:
        return jsonify({'error': 'No data to save'})
    doc_name = f"Project_{final_data.get('project_name', 'Untitled')}_{date.today()}"
    doc = {'name': doc_name, 'mimeType': 'application/vnd.google-apps.document'}
    file = drive_service.files().create(body=doc).execute()
    doc_id = file['id']
    # Insert content
    content_str = json.dumps(final_data, indent=2)
    requests = [{'insertText': {'location': {'index': 1}, 'text': content_str}}]
    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    return jsonify({'doc_url': f"https://docs.google.com/document/d/{doc_id}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
