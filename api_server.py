from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import openai
import os

openai.api_key = os.environ.get('OPENAI_API_KEY')

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from queue import Queue
import base64

class BufferStream(Queue):
    def __init__(self, buffer_max_size: int = 5):
        super().__init__(maxsize=buffer_max_size)

    def read(self):
        return self.get()

def transcribe_audio_stream(stream):
    client = speech.SpeechClient()
    config=speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_speaker_diarization=True,
        diarization_speaker_count=2
    )
    stream_buffer = BufferStream()

    for chunk in stream:
        stream_buffer.put(chunk)
        if stream_buffer.full():
            audio_content = stream_buffer.get_nowait() 
            request = speech.StreamingRecognizeRequest(audio_content=audio_content)
            responses = client.streaming_recognize(config, [request])
            for response in responses:
                print(response)
                
def convert_text_to_speech(text: str):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US",
                                              ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    audio_data = response.audio_content
    socketio.emit('response', {'audio_data': base64.b64encode(audio_data).decode()})

def storeConversationData(conversations):
    [print(f"User: {dialogue['User']}\nResponse: {dialogue['Response']}") for dialogue in conversations]

def generate_ai_response(user_message: str) -> str:   
    conversation = {
        'messages': [{"role": "user", "content": f"{user_message}"}]
    }

    response = openai.ChatCompletion.create(model="gpt-4", messages=conversation['messages'],
                                            max_tokens=150)
    return response['choices'][0]['message']['content']

app = Flask(__name__, static_folder='talkasaurus-react/build')
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@socketio.on('message')
def handle_message(data):
    dialogsCollection = []
    user_message = data['message']
    try:
        response = generate_ai_response(user_message)
        convert_text_to_speech(response)
        socketio.emit('response', {'response': response, 'message': user_message})
        dialogsCollection.append({
            "User": user_message,
            "Response": response
        })
    except Exception as e:
        # this could include logging to a file/logscollector
        print(f"Error while generating AI response: {str(e)}")

    storeConversationData(dialogsCollection)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0"', port=int(os.getenv('PORT', 5000)))