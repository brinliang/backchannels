# Setup Instructions

For macOS, first use homebrew to install portaudio.
```
brew install portaudio
```

Create a new conda environment and install the required packages.
```
conda create -n backchannels
conda activate backchannels
conda install pip
pip install -r requirements.txt
```

Get your API key from OpenAI (https://platform.openai.com/account/api-keys).
Copy the API key and paste it into the command
```
echo "openai_key = 'YOUR_API_KEY_HERE'" > config.py
```

The ipython notebook contains implementation details.
To run the turn based demo, run
```
python turn-based.py
```

To run the real time demo, get an API key from AssemblyAI (https://www.assemblyai.com/app).
Copy the API key and paste it into the command
```
echo "assembly_key = 'YOUR_API_KEY_HERE'" >> config.py
```
Then run
```
python real-time.py
```
