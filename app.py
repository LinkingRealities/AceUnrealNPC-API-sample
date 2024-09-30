import os
from threading import Thread

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

A2F_API_URL = "http://localhost:8011"
A2F_SOLVER_FILEPATH = "C:/Users/UA/Desktop/arkit_solver.usd"


def initialize():
    "Requires Audio2Face to already be running"

    # Load the solver file in Audio2Face (from step 3)
    response = requests.post(
        f"{A2F_API_URL}/A2F/USD/Load",
        headers={
            "Content-Type": "application/json",
        },
        json={"file_name": A2F_SOLVER_FILEPATH},
        timeout=20,
    )

    if response.status_code != 200:
        return (
            jsonify({"error": "Failed to load solver in A2F. Make sure it's running"}),
            response.status_code,
        )

    # Activate the LiveLink Streaming
    response = requests.post(
        f"{A2F_API_URL}/A2F/Exporter/ActivateStreamLivelink",
        headers={
            "Content-Type": "application/json",
        },
        json={"node_path": "/World/audio2face/StreamLivelink", "value": "true"},
        timeout=20,
    )

    # Set the Audio2Face root path (the file dir where the audios will be stored)
    response = requests.post(
        f"{A2F_API_URL}/A2F/Player/SetRootPath",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "a2f_player": "/World/audio2face/Player",
            "dir_path": TEMP_AUDIO_DIR,
        },
        timeout=20,
    )


def send_to_a2f(filepath):
    # Set the track in Audio2Face
    response = requests.post(
        f"{A2F_API_URL}/A2F/Player/SetTrack",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "a2f_player": "/World/audio2face/Player",
            "file_name": os.path.basename(filepath),
            "time_range": [0, -1],
        },
        timeout=20,
    )

    # Start generating the animation
    response = requests.post(
        f"{A2F_API_URL}/A2F/Player/Play",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "a2f_player": "/World/audio2face/Player",
        },
        timeout=20,
    )

    if response.status_code != 200:
        return (
            jsonify({"error": "Failed to set track in A2F"}),
            response.status_code,
        )


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
        # Then saves it as a file called output.wav
        generate_audio(completion.choices[0].message.content)

        # Send Audio2Face request in the background
        thread = Thread(
            target=send_to_a2f, args=(os.path.join(TEMP_AUDIO_DIR, "output"))
        )
        thread.start()

        print(completion.choices[0].message.content)

        return jsonify({"response": completion.choices[0].message.content}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Setup Audio2Face
initialize()
