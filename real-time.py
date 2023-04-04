import websockets
import asyncio
import base64
import json
import config

import pyaudio

import openai
import pyttsx3

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
openai.api_key = config.openai_key
engine = pyttsx3.init()

# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)

# the AssemblyAI endpoint we're going to hit
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

# prompt to use for gpt responses
prompt = 'Respond with a verbal backchannel as if you are actively listening to someone say "{}"'

async def send_receive():

    print(f'Connecting websocket to url ${URL}')

    async with websockets.connect(
            URL,
            extra_headers=(("Authorization", config.assembly_key),),
            ping_interval=10,
            ping_timeout=40
    ) as _ws:

        await asyncio.sleep(0.1)
        print("Receiving SessionBegins ...")

        session_begins = await _ws.recv()
        print(session_begins)
        print("Sending messages ...")

        async def send():
            while True:
                try:
                    data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                    data = base64.b64encode(data).decode("utf-8")
                    json_data = json.dumps({"audio_data": str(data)})
                    await _ws.send(json_data)

                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break

                except Exception as e:
                    print(e)
                    assert False, "Not a websocket 4008 error"

                await asyncio.sleep(0.01)

            return True

        async def receive():

            transcript = ''
            response = ''

            while True:
                try:
                    transcript = await _ws.recv()
                    print('Transcript: ', json.loads(transcript)['text'])

                    # play response if sentence ends
                    if json.loads(transcript)['message_type'] == 'FinalTranscript':
                        engine.say(response)
                        engine.runAndWait()
                        engine.stop()

                    # create response to play
                    response = openai.Completion.create(
                        model='text-davinci-003',
                        prompt=prompt.format(json.loads(transcript)['text']),
                        max_tokens=256,
                    )['choices'][0]['text'].strip()
                    print('Response: ', response)

                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break

                except Exception as e:
                    print(e)
                    assert False, "Not a websocket 4008 error"

        send_result, receive_result = await asyncio.gather(send(), receive())

while True:
    asyncio.run(send_receive())
