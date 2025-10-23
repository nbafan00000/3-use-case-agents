from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Replace with your file paths and agent IDs
file1 = client.files.create(file=open("elevance_10k.pdf", "rb"), purpose="assistants")
file2 = client.files.create(file=open("capability_model.xlsx", "rb"), purpose="assistants")

# Attach to Agent 2
client.beta.assistants.update(assistant_id="asst_8onKwY0XOHcshizOLuEGgOHU", file_ids=[file1.id, file2.id])
# Attach to Agent 3
client.beta.assistants.update(assistant_id="asst_43nQoLPoAIk3p8CV7D2zauId", file_ids=[file1.id, file2.id])