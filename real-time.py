import websockets
import asyncio
import base64
import json
import config
import pyaudio
import openai
from aioconsole import ainput
from gtts import gTTS
import os

# prompt to use for gpt responses
prompt = 'respond with a verbal backchannel to "{}"'

# toggle true for automatic and false for manual backchanneling timing
pause_activated = True

# change this to change response update rate
FRAMES_PER_BUFFER = 1600

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
openai.api_key = config.openai_key

# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)

# assembly api endpoint
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

transcript = ''
response = ''


async def generate_response():
    while True:
        try:
            # generate response from gpt3
            request = await openai.Completion.acreate(
                model='text-davinci-003',
                prompt=prompt.format(transcript),
                max_tokens=256,
            )
            # update response
            global response
            response = request['choices'][0]['text'].strip()
            print('transcript: ', transcript)
            print('response: ', response)

            # create audio response
            tts = gTTS(text=response, lang='en')
            tts.save('response.mp3')

        except:
            print('error')

        await asyncio.sleep(0.01)


async def play_response():
    # press any key to play a response prepared at a given moment
    if not pause_activated:
        while True:
            input = await ainput('')
            if input == '1':
                os.system('afplay response.mp3')

            await asyncio.sleep(0.01)


async def send_receive():

    print(f'Connecting websocket to url ${URL}')

    # connect to assembly endpoint with websockets
    async with websockets.connect(
            URL,
            extra_headers=(("Authorization", config.assembly_key),),
            ping_interval=5,
            ping_timeout=20
    ) as _ws:

        await asyncio.sleep(0.1)
        print("Receiving SessionBegins ...")

        session_begins = await _ws.recv()
        print(session_begins)
        print("Sending messages ...")

        # send chunk of audio to endpoint
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

        # receive transcription
        async def receive():

            while True:
                try:
                    assembly = await _ws.recv()
                    global transcript

                    # play an audio response
                    if pause_activated and json.loads(assembly)['message_type'] == 'FinalTranscript' and os.path.exists('response.wav'):
                        os.system('afplay response.wav')
                        os.remove('response.wav')
                        global response
                        response = ''
                        transcript = ''
                    else:
                        transcript = json.loads(assembly)['text']

                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break

                except Exception as e:
                    print(e)
                    assert False, "Not a websocket 4008 error"

        send_result, receive_result = await asyncio.gather(send(), receive())


# run functions asynchronously 
loop = asyncio.get_event_loop()
loop.create_task(generate_response())
loop.create_task(send_receive())
loop.create_task(play_response())
loop.run_forever()
