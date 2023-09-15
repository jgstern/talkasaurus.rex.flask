from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import openai

openai.api_key = 'my-api-key'

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
    response = openai.Completion.create(
        engine="text-davinci-003", 
        prompt=user_message, 
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()


if __name__ == '__main__':
    socketio.run(app)