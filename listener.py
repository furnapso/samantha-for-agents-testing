import base64
import json
import logging
import argparse
import uuid
import os
import io

from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import audio_config
from google.cloud.dialogflowcx_v3beta1.types import session
from pydub import AudioSegment
from pydub.playback import play
from flask import Flask
from flask_sockets import Sockets, Rule

import queue
import threading
from dialogflow_stream import DialogflowStream

input_audio_config = audio_config.InputAudioConfig(
    audio_encoding=audio_config.AudioEncoding.AUDIO_ENCODING_MULAW,
    sample_rate_hertz=8000,
    single_utterance=True
)

#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "just use environmental variables bro"

session_id = str(uuid.uuid4())

app = Flask(__name__)
sockets = Sockets(app)

HTTP_SERVER_PORT = 5000

@sockets.route('/media')
def echo(ws):

    count = 0
    while not ws.closed:
        # lol what was i thinking
        if 'dialogflow_thread' in locals():
            if not dialogflow_thread.is_alive():
                audio_queue = queue.Queue()
                dialogflow_stream = DialogflowStream(audio_queue, session_id)
                dialogflow_thread = threading.Thread(target=dialogflow_stream.start)
                dialogflow_thread.start()
        else:
            audio_queue = queue.Queue()
            dialogflow_stream = DialogflowStream(audio_queue, session_id)
            dialogflow_thread = threading.Thread(target=dialogflow_stream.start)
            dialogflow_thread.start()

        message = ws.receive()
        if message is None:
            continue

        # Messages are a JSON encoded string
        data = json.loads(message)

        if data['event'] == "media":
            # Add the media to the stream
            payload = data['media']['payload']
            chunk = base64.b64decode(payload)
            audio_queue.put(chunk)
            if not dialogflow_thread.is_alive():
                continue
                
        if data['event'] == "closed":
            print("wait wtf") # TODO
            break

    # yeah ik block comments are a thing shut up

    #responses = session_client.streaming_detect_intent(requests=request_generator())

    #print("=" * 20)
    #for response in responses:
    #    print(f'C Intermediate transcript final: "{response.recognition_result.transcript}".')

    # Note: The result from the last response is the final transcript along
    # with the detected content.
    #response = response.detect_intent_response
    #with open(f"responses/response_final_dumps.json", "w") as f:
    #    f.write(str(response))
    #print(f"Query text: {response.query_result.transcript}")
    #response_messages = [
    #    " ".join(msg.text.text) for msg in response.query_result.response_messages
    #]
    #print(f"Response text: {' '.join(response_messages)}\n")
    #audio_bytes = response.output_audio
    #recording = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
    #recording.export('combined_response.mp3', format='mp3')

sockets.url_map.add(Rule('/media', endpoint=echo, websocket=True))

if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    print("Server listening on: http://localhost:" + str(HTTP_SERVER_PORT))
    server.serve_forever()
