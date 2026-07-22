from mistralai.client import Mistral

from config import (
    MISTRAL_API_KEY,
    MODEL_NAME
)

client = Mistral(
    api_key=MISTRAL_API_KEY
)


def ask_mistral(prompt, system=None, temperature=0):

    messages = []

    if system:
        messages.append({
            "role": "system",
            "content": system
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = client.chat.complete(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature
    )

    return response.choices[0].message.content