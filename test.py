from mistralai.client import Mistral
from config import MISTRAL_API_KEY

client = Mistral(api_key=MISTRAL_API_KEY)

response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {
            "role": "user",
            "content": "Hello"
        }
    ]
)

print(response)