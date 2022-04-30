import sounddevice as sd
import pyaudio

p = pyaudio.PyAudio()

for i in range(0, p.get_host_api_count()):
    print(p.get_host_api_info_by_index(i))

print(sd.query_devices())
