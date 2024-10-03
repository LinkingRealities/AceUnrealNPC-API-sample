import os

from dotenv import load_dotenv
import requests
from flask import Flask, jsonify, request
from openai import OpenAI
from tts import generate_audio

load_dotenv()

client = OpenAI()

# Here we'll story all the conversation with the LLM
# You can think of this as the character's memory
# We initialize it with a pre-prompt
history = [
    {
        "role": "system",
        # In the next field, describe your character, what does he/she know, behaviour, etc...
        "content": """You are a female merchant called Sally. Chat in a human way,
        don't sound robotic or scripted. Don't make your responses longer than 100 words
        ...
        ...
        ...
        """,
    }
]

app = Flask(__name__)

TEMP_AUDIO_DIR = os.path.dirname(__file__)


@app.route("/response", methods=["POST"])
def generate_response():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return (
                jsonify(
                    {
                        "error": 'Invalid request. Please send a JSON body with a "text" field.'
                    }
                ),
                400,
            )

        # User input
        text = data["text"]

        # We add the input to the chat history, so the NPC "remembers" it
        history.append(
            {
                "role": "user",
                "content": text,
            }
        )

        # generate a response
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
        )

        history.append(
            {
                "role": completion.choices[0].message.role,
                "content": completion.choices[0].message.content,
            }
        )

        # This function generates audio from Eleven Labs
        # Then saves it as a file in the folder passed as an argument
        audio_filepath = generate_audio(completion.choices[0].message.content, TEMP_AUDIO_DIR)

        print(completion.choices[0].message.content)

        return jsonify({"response": completion.choices[0].message.content, "audio": audio_filepath}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
