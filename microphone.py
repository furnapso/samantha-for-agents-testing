import time
import threading
import pyaudio
import wave
import queue
import logging
from datetime import datetime


class MicrophoneStream():
    def __init__(self, queue: queue.Queue) -> None:
        self.queue = queue

    def start(self):
        logging.info("Recording started")
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 24000
        CHUNK = 1024

        audio = pyaudio.PyAudio()

        header = self.genHeader(RATE, 16, CHANNELS)
        self.queue.put(header)

        # start Recording
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK, input_device_index=1)

        while True:
            chunk = stream.read(CHUNK)
            self.queue.put(chunk)

    def _callback(self, data, frame_count, time_info, status):
        self.queue.put(data)
        return None, pyaudio.paContinue

    def start_file(self):
        logging.info("Starting audio file")
        with open('file.wav', 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.queue.put(chunk)

    def genHeader(self, sampleRate, bitsPerSample, channels):
        # Some veeery big number here instead of: #samples * channels * bitsPerSample // 8
        datasize = 10240000
        # (4byte) Marks file as RIFF
        o = bytes("RIFF", 'ascii')
        # (4byte) File size in bytes excluding this and RIFF marker
        o += (datasize + 36).to_bytes(4, 'little')
        # (4byte) File type
        o += bytes("WAVE", 'ascii')
        # (4byte) Format Chunk Marker
        o += bytes("fmt ", 'ascii')
        # (4byte) Length of above format data
        o += (16).to_bytes(4, 'little')
        # (2byte) Format type (1 - PCM)
        o += (1).to_bytes(2, 'little')
        # (2byte)
        o += (channels).to_bytes(2, 'little')
        # (4byte)
        o += (sampleRate).to_bytes(4, 'little')
        o += (sampleRate * channels * bitsPerSample //
              8).to_bytes(4, 'little')  # (4byte)
        o += (channels * bitsPerSample // 8).to_bytes(2,
                                                      'little')               # (2byte)
        # (2byte)
        o += (bitsPerSample).to_bytes(2, 'little')
        # (4byte) Data Chunk Marker
        o += bytes("data", 'ascii')
        # (4byte) Data size in bytes
        o += (datasize).to_bytes(4, 'little')
        return o

    def start_sync(self):
        logging.info("Recording started")
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 24000
        CHUNK = 1024

        audio = pyaudio.PyAudio()

        header = self.genHeader(RATE, 16, CHANNELS)
        self.queue.put(header)

        # start Recording
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK, input_device_index=1)

        yield self.genHeader(RATE, 16, CHANNELS)

        while True:
            chunk = stream.read(1024)
            if not chunk:
                break
            yield chunk


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    q = queue.Queue()
    stream = MicrophoneStream(q)
    stream_thread = threading.Thread(target=stream.start)
    stream.start()

    start = datetime.now()
    frames = []

    while (datetime.now() - start).total_seconds() < 5:
        frames.append(q.get())

    with open('test.wav', 'wb') as f:
        f.write(b''.join(frames))
