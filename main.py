import whisper
import streamlit as st
from moviepy.video.io.VideoFileClip import VideoFileClip
import tempfile
import os

st.title("Video Transcription App")

# File uploader
uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov'])

if uploaded_file is not None:
    # Create a temporary file to save the uploaded video
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        tmp_file.write(uploaded_file.read())
        video_path = tmp_file.name

    try:
        with st.spinner('Processing video...'):
            # Extract audio from video
            video = VideoFileClip(video_path)
            
            # Create temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            
            # Load model and transcribe
            model = whisper.load_model("base")
            result = model.transcribe(temp_audio)
            
            # Display transcription
            st.subheader("Transcription:")
            st.write(result["text"])
            
            # Cleanup
            video.close()
            os.unlink(video_path)
            os.unlink(temp_audio)
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
