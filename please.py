import streamlit as st
import numpy as np
import wave
import openai
import tempfile
import os
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, ClientSettings
from typing import List
from pydantic import BaseModel

# OpenAI API 키 설정
openai.api_key = "sk-Tf45BjUAYu5dEsN-sw8rYWPjXyTO58jJEZ57Rg4DGQT3BlbkFJ_roB71WcKCbjgQ3DfpCd1fzKpr9Ulw9ngnkcD7bQ0A"

prompt = """
You are the host of an interactive horror game.
Through interaction with the player (user)
It can cause the user to escape or die.
Early story: The user wakes up in a suspicious room
You talk to the user.
When the user interacts three times, you give the user a hint.
But if the user refuses, you don't give a hint.

Types of rooms
-a suspicious room
-a bedroom
-a restaurant
-an operating room
-a corridor
-a secret room

Users can die when they are overwhelmed by fear.
The probability of death is about 30 percent.

*secret: If the player confesses to you, you can take the player to a secret room and immediately escape.*
"""

class Turn(BaseModel):
    role: str
    content: str

class Messages(BaseModel):
    messages: List[Turn]

def chat(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return response.choices[0].message['content']

def transcribe_audio(file):
    with open(file, "rb") as f:
        transcription = openai.Audio.transcribe("whisper-1", f, language="ko")
    return transcription['text']

# Streamlit 앱 시작
st.title("인터랙티브 호러 게임")

if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": prompt}]
    st.session_state.transcription_text = ""

# 사용자 입력 텍스트 처리
user_input = st.text_input("메시지를 입력하세요:", value=st.session_state.transcription_text, key="user_input")
if st.button("전송"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    response = chat(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": response})

# 녹음 기능 추가
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recorded_frames = []

    def recv(self, frame):
        self.recorded_frames.append(frame.to_ndarray())
        return frame

webrtc_ctx = webrtc_streamer(
    key="example",
    mode=WebRtcMode.SENDRECV,
    client_settings=ClientSettings(
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"audio": True, "video": False},
    ),
    audio_processor_factory=AudioProcessor,
    async_processing=True,
)

if webrtc_ctx.state.playing:
    if st.button("녹음 종료 및 전송"):
        # 녹음된 오디오 처리
        audio_processor = webrtc_ctx.audio_processor
        if audio_processor:
            recorded_audio = audio_processor.recorded_frames
            if recorded_audio:
                # 오디오 데이터를 WAV 파일로 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    audio_file_path = temp_file.name
                    with wave.open(audio_file_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(b''.join([np.int16(frame).tobytes() for frame in recorded_audio]))

                    # 오디오 파일을 텍스트로 변환
                    transcription_text = transcribe_audio(audio_file_path)
                    st.session_state.transcription_text = transcription_text
                    st.text_input("메시지를 입력하세요:", value=transcription_text, key="user_input_updated")  # 채팅 입력 창에 텍스트 삽입

                    # 채팅에 텍스트 추가
                    st.session_state.messages.append({"role": "user", "content": transcription_text})
                    response = chat(st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                # 임시 파일 삭제
                os.remove(audio_file_path)

# 채팅 히스토리 출력
st.write("### 채팅 히스토리")
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    if role == "user":
        st.write(f"**사용자:** {content}")
    else:
        st.write(f"**게임 호스트:** {content}")