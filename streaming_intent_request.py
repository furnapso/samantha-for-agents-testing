#!/usr/bin/env python

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DialogFlow API Detect Intent Python sample with audio files processed as an audio stream.

Examples:
  python detect_intent_stream.py -h
  python detect_intent_stream.py --agent AGENT \
  --session-id SESSION_ID --audio-file-path resources/hello.wav
"""
import config

from email.mime import audio
import os
import argparse
import uuid

from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import audio_config
from google.cloud.dialogflowcx_v3beta1.types import session
from google.cloud.dialogflowcx_v3beta1.types.session import StreamingRecognitionResult

from microphone import MicrophoneStream
import threading
import queue
import logging

logging.basicConfig(level=logging.INFO)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.GOOGLE_APPLICATION_CREDENTIALS


def detect_intent_stream(agent, session_id, language_code):
    """Returns the result of detect intent with streaming audio as input.

    Using the same `session_id` between requests allows continuation
    of the conversation."""
    session_path = f"{agent}/sessions/{session_id}"
    print(f"Session path: {session_path}\n")
    client_options = None
    agent_components = AgentsClient.parse_agent_path(agent)
    location_id = agent_components["location"]
    if location_id != "global":
        api_endpoint = f"{location_id}-dialogflow.googleapis.com:443"
        print(f"API Endpoint: {api_endpoint}\n")
        client_options = {"api_endpoint": api_endpoint}
    session_client = SessionsClient(client_options=client_options)

    input_audio_config = audio_config.InputAudioConfig(
        audio_encoding=audio_config.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
        sample_rate_hertz=24000,
        single_utterance=True
    )

    audio_queue = queue.Queue()
    microphone_stream = MicrophoneStream(audio_queue)
    mic_thread = threading.Thread(target=microphone_stream.start)
    mic_thread.start()

    def request_generator():
        audio_input = session.AudioInput(config=input_audio_config)
        query_input = session.QueryInput(
            audio=audio_input, language_code=language_code)
        voice_selection = audio_config.VoiceSelectionParams()
        synthesize_speech_config = audio_config.SynthesizeSpeechConfig()
        output_audio_config = audio_config.OutputAudioConfig()

        # Sets the voice name and gender
        voice_selection.name = "en-GB-Standard-A"
        voice_selection.ssml_gender = (
            audio_config.SsmlVoiceGender.SSML_VOICE_GENDER_FEMALE
        )

        synthesize_speech_config.voice = voice_selection

        # Sets the audio encoding
        output_audio_config.audio_encoding = (
            audio_config.OutputAudioEncoding.OUTPUT_AUDIO_ENCODING_UNSPECIFIED
        )
        output_audio_config.synthesize_speech_config = synthesize_speech_config

        # The first request contains the configuration.
        yield session.StreamingDetectIntentRequest(
            session=session_path,
            query_input=query_input,
            output_audio_config=output_audio_config,
        )

        # Here we are reading small chunks of audio data from a local
        # audio file.  In practice these chunks should come from
        # an audio input device.
        # while True:
        #     chunk = audio_queue.get()
        #     logging.info(chunk)
        #     if audio_queue.empty():
        #         break
        # for chunk in microphone_stream.start_sync():
        for chunk in iter(audio_queue.get, None):
            # The later requests contains audio data.
            audio_input = session.AudioInput(audio=chunk)
            query_input = session.QueryInput(audio=audio_input)
            yield session.StreamingDetectIntentRequest(query_input=query_input)

    responses = session_client.streaming_detect_intent(
        requests=request_generator())

    print("=" * 20)
    should_stop_next = False
    for response in responses:
        print(
            f'Intermediate transcript: "{response.recognition_result.transcript}".')
        if should_stop_next:
            break
        should_stop_next = response.recognition_result.is_final

    # Note: The result from the last response is the final transcript along
    # with the detected content.
    response = response.detect_intent_response
    print(f"Query text: {response.query_result.transcript}")
    response_messages = [
        " ".join(msg.text.text) for msg in response.query_result.response_messages
    ]
    print(f"Response text: {' '.join(response_messages)}\n")


# [END dialogflow_detect_intent_stream]

if __name__ == "__main__":
    agent = config.AGENT
    session_id = uuid.uuid4()
    language_code = 'en-au'
    detect_intent_stream(agent, session_id, language_code)
