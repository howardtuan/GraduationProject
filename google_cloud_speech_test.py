
import queue
import re
import sys

from google.cloud import speech

import pyaudio

from pygame import *

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

# UI 介面參數
SCREENWIDTH = 800
SCREENHEIGHT = 600 

class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(format = pyaudio.paInt16, channels = 1, rate = self._rate, input = True, frames_per_buffer = self._chunk, stream_callback = self._fill_buffer)
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


if __name__ == "__main__":
    
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = "zh-TW" 

    client = speech.SpeechClient.from_service_account_json('assets/auth/key.json')
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    # UI initialization
    init()
    user_interface = display.set_mode((SCREENWIDTH, SCREENHEIGHT))
    display.set_caption('測試')
    user_interface.fill((255, 255, 255))
    head_font = font.Font("assets/font/Kaiu.ttf", 24)
    display.update()
    text = ""
    
    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content = content) for content in audio_generator )

        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.
        num_chars_printed = 0
        
        for response in responses:
            for events in event.get():
                if events.type == QUIT:
                    quit()
                    sys.exit()
            
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue
            
            # reset UI
            user_interface.fill((255, 255, 255))
            
            transcript = result.alternatives[0].transcript
            overwrite_chars = " " * (num_chars_printed - len(transcript))

            if not result.is_final:
                text = transcript + overwrite_chars
                sys.stdout.write(transcript + overwrite_chars + "\r")
                sys.stdout.flush()
                num_chars_printed = len(transcript)

            else:
                text = transcript + overwrite_chars
                print(text)
                if re.search(r"\b(exit|quit)\b", transcript, re.I):
                    print("Exiting..")
                    break
                num_chars_printed = 0
                
            text_surface = head_font.render(text, True, (0, 0, 0))
            user_interface.blit(text_surface, (10, 10))
            display.update()