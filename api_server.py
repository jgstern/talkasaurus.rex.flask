from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import openai
import os

# TODO: Make sure this key is correctly set and safely stored
openai.api_key = os.environ.get('OPENAI_API_KEY')

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech


#This would require an audio stream chunked into parts to work most effectively, which would require changes based on the specific implementation of audio input.
def transcribe_audio_stream(stream):
    client = speech.SpeechClient()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_speaker_diarization=True,
        diarization_speaker_count=2,
    )

    requests = [
        speech.StreamingRecognizeRequest(audio_content=chunk)
        for chunk in stream
    ]

    responses = client.streaming_recognize(config, requests)
    # TODO Add processing logic
    for response in responses:
        # TODO Process responses


def convert_text_to_speech(text):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput({"text": text})

    # More voice settings can be added for better speech synthesis
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)

    # Audio config settings can be updated for better audio output
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    # Creating the speech synthesis response
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the synthesized speech to a file
    # TODO: create a unique name every time this method gets called or directly stream the audio to the frontend, eliminating the need to manage the audio files
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
    print("Audio content written to file output.mp3")


app = Flask(__name__, static_folder='talkasaurus-react/build')
socketio = SocketIO(app)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@socketio.on('message')
def handle_message(data):
    # Send the message to OpenAI's GPT4 model and produce a response
    response = generate_ai_response(data['message'])

    # Send the AI response back to the client
    socketio.emit('response', {'message': response})

def generate_ai_response(user_message): 
    #TODO: error handling if there's an issue with the GPT API call
    response = openai.Completion.create(
        engine="text-davinci-003", 
        prompt=user_message, 
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()


if __name__ == '__main__':
    socketio.run(app)