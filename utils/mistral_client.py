from mistralai import Mistral

from config import (
    MISTRAL_API_KEY,
    MODEL_NAME
)

client = Mistral(
    api_key=MISTRAL_API_KEY
)


def ask_mistral(prompt):

    response = client.chat.complete(

        model=MODEL_NAME,

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]

    )

    return response.choices[0].message.content