import os
from huggingface_hub import InferenceClient


client = InferenceClient(
    model="aaditya/Llama3-OpenBioLLM-70B",
    token=os.environ["HUGGINGFACE_TOKEN"],
    provider="nebius",  # Optional unless specified in docs
)

completion = client.chat.completions.create(
    model="aaditya/Llama3-OpenBioLLM-70B",
    messages=[
        {
            "role": "system",
            "content": "You are OpenBioLLM, a helpful biomedical assistant developed by Saama AI Labs."
        },
        {
            "role": "user",
            "content": "How do you interpret elevated ALT and AST in a liver function test?"
        }
    ],
    max_tokens=512
)

print(completion.choices[0].message.content)
