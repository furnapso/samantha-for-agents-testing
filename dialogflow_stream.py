import queue
import logging
import io
import os
import time
import base64

from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import audio_config
from google.cloud.dialogflowcx_v3beta1.types import session
from header import generate_header

from pydub import AudioSegment
from pydub.playback import play

#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "just use environmental variables bro"

class DialogflowStream():
    def __init__(self, queue: queue.Queue, session_id) -> None:
        self.queue = queue
        self.session_id = session_id
        
    def start(self):
        self.queue.put(generate_header(8000, 8, 1))

        agent = "projects/sam-for-agents/locations/australia-southeast1/agents/a62e0993-d8d7-4dac-b6e8-2d3948ff6291"
        language_code = "en-US"
        session_path = f"{agent}/sessions/{self.session_id}"
        #print(f"Session path: {session_path}\n")
        client_options = None
        agent_components = AgentsClient.parse_agent_path(agent)
        location_id = 'australia-southeast1'
        if location_id != "global":
            api_endpoint = f"{location_id}-dialogflow.googleapis.com:443"
            #print(f"API Endpoint: {api_endpoint}\n")
            client_options = {"api_endpoint": api_endpoint}
        session_client = SessionsClient(client_options=client_options)
        input_audio_config = audio_config.InputAudioConfig(
            audio_encoding=audio_config.AudioEncoding.AUDIO_ENCODING_MULAW,
            sample_rate_hertz=8000,
            single_utterance=True
        )

        def request_generator():
            last_queue_size = 0
            audio_input = session.AudioInput(config=input_audio_config)
            query_input = session.QueryInput(audio=audio_input, language_code=language_code)
            voice_selection = audio_config.VoiceSelectionParams()
            synthesize_speech_config = audio_config.SynthesizeSpeechConfig()
            output_audio_config = audio_config.OutputAudioConfig()

            # Sets the voice name and gender
            voice_selection.name = "en-AU-Wavenet-C"
            voice_selection.ssml_gender = (
                audio_config.SsmlVoiceGender.SSML_VOICE_GENDER_FEMALE
            )

            synthesize_speech_config.voice = voice_selection
            synthesize_speech_config.pitch = -2.4
            synthesize_speech_config.speaking_rate = 0.96

            # Sets the audio encoding
            output_audio_config.audio_encoding = (
                audio_config.OutputAudioEncoding.OUTPUT_AUDIO_ENCODING_MULAW
            )
            output_audio_config.synthesize_speech_config = synthesize_speech_config
            
            yield session.StreamingDetectIntentRequest(
                session=session_path,
                query_input=query_input,
                output_audio_config=output_audio_config,
            )

            consecutive_count = 0
            for chunk in iter(self.queue.get, None):
                if self.queue.empty():
                    consecutive_count += 1
                if consecutive_count == 40:
                    print("Break")
                    break
                audio_input = session.AudioInput(audio=chunk)
                query_input = session.QueryInput(audio=audio_input)
                yield session.StreamingDetectIntentRequest(query_input=query_input)
            #print("When do I hit this?")
        
        responses = session_client.streaming_detect_intent(requests=request_generator())

        print("=" * 20)
        for response in responses:
            print(f'Intermediate transcript: "{response.recognition_result.transcript}".')

        # Note: The result from the last response is the final transcript along
        # with the detected content.
        response = response.detect_intent_response
        print(f"Query text: {response.query_result.transcript}")
        response_messages = [
            " ".join(msg.text.text) for msg in response.query_result.response_messages
        ]
        print(f"Response text: {' '.join(response_messages)}")
        audio_bytes = response.output_audio
        with open("audio_bytes_raw.txt", "wb") as f:
            f.write(audio_bytes[58:])
        with open("audio_bytes_b64.txt", "w") as f:
            f.write(str(base64.b64encode(audio_bytes[58:])))
        #recording = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
        #recording.export('dialogflow_stream.wav', format='wav')
        return

            
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import uuid, threading
    s = str(uuid.uuid4())

    q = queue.Queue()
    stream = DialogflowStream(q, s)
    print(str(stream))
    stream.start()
    print("Done")