import websockets
import asyncio
import base64
import json
import pyaudio
import openai
from aioconsole import ainput
from gtts import gTTS
import os
import wave
import config

# directory for data
directory = 'data'

# prompt to use for gpt responses
prompt = 'respond with a verbal backchannel to [" {} "]'

# toggle true for automatic and false for manual backchanneling timing
pause_activated = True

# change this to change response update rate
FRAMES_PER_BUFFER = 1600

# audio settings - make sure audio data matches these settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
openai.api_key = config.openai_key

# assembly api endpoint
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    output=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)

# globals
transcript = ''
response = ''
end = False

async def test_audio_file(filename):
    # reset globals
    global transcript
    global response
    global end
    transcript = ''
    response = ''
    end = False

    # set up logs
    full_results = open('results/full/' + filename.split('.')[0] + '.txt', 'a')
    main_results = open('results/main/' + filename.split('.')[0] + '.txt', 'a')

    # open audio file
    wf = wave.open(os.path.join(directory, filename), 'rb')

    async def send_receive():

        print(f'Connecting websocket to url ${URL}')

        # connect to endpoint
        async with websockets.connect(
                URL,
                extra_headers=(("Authorization", config.assembly_key),),
                ping_interval=5,
                ping_timeout=20
        ) as _ws:

            await asyncio.sleep(0.1)
            print("Receiving Session Begins ...")

            session_begins = await _ws.recv()
            print(session_begins)
            print("Sending messages ...")

            # send audio chunk to endpoint
            async def send():
                while True:
                    try:
                        data = wf.readframes(FRAMES_PER_BUFFER)
                        stream.write(data)
                        data = base64.b64encode(data).decode("utf-8")
                        json_data = json.dumps({"audio_data": str(data)})
                        await _ws.send(json_data)

                    except websockets.exceptions.ConnectionClosedError as e:
                        # print('END 1')
                        # print(e)
                        # assert e.code == 4008
                        break

                    except Exception as e:
                        # print('END 2')
                        # print(e)
                        # assert False, "Not a websocket 4008 error"
                        break


                    await asyncio.sleep(0.01)

                global end
                end = True
                return True


            # receive transcription
            async def receive():

                while True:
                    try:
                        assembly = await _ws.recv()
                        global transcript

                        if pause_activated and json.loads(assembly)['message_type'] == 'FinalTranscript' and os.path.exists('response.wav'):
                            # play response on transcript end
                            global response
                            # log results
                            main_results.write('user: ' + transcript + '\n')
                            main_results.write('bot: ' + response + '\n')
                            full_results.write('user: ' + transcript + '\n')
                            full_results.write('bot (spoken): ' + response + '\n')
                            os.system('afplay response.wav')
                            os.remove('response.wav')
                            response = ''
                            transcript = ''
                        else:
                            # update transcription to respond to otherwise
                            transcript = json.loads(assembly)['text']
                            full_results.write('user: ' + transcript + '\n')
                            full_results.write('bot (prepared): ' + response + '\n')

                    except websockets.exceptions.ConnectionClosedError as e:
                        # print('END 3')
                        # print(e)
                        # assert e.code == 4008
                        break

                    except Exception as e:
                        # print('END 4')
                        # print(e)
                        # assert False, "Not a websocket 4008 error"
                        break

            send_result, receive_result = await asyncio.gather(send(), receive())

            global end
            end = True
            return


    async def generate_response():
        global end
        while not end:
            try:
                # generate response from gpt3
                request = await openai.Completion.acreate(
                    model='text-davinci-003',
                    prompt=prompt.format(transcript),
                    max_tokens=256,
                )
                global response
                response = request['choices'][0]['text'].strip()
                print('transcript: ', transcript)
                print('response: ', response)
                # create audio response
                tts = gTTS(text=response, lang='en')
                tts.save('response.wav')

            except:
                # print('END 5')
                # print('error')
                break

            await asyncio.sleep(0.01)
        
        return

    async with asyncio.TaskGroup() as tg:
        sr = tg.create_task(send_receive())
        gen = tg.create_task(generate_response())

    return


for filename in os.listdir(directory):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_audio_file(filename))