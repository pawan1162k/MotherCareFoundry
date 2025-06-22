from huggingface_hub import login
from utils.config import HUGGINGFACE_TOKEN

login(token=HUGGINGFACE_TOKEN)
print("Token login successful")