# import zipfile
# import os
# import tempfile
# import whisper

# # Specify the input PPTX file and output ZIP file names
# file = '/Users/tushargupta/Downloads/Lecture 1_Definition and conceptualization.pptx'  # Replace with your PPTX file path
# file = os.path.splitext(file)[0] + '.zip'

# # Create dictionary to store audio files
# audio_files = {}

# # Create temporary directory for extraction
# temp_dir = tempfile.mkdtemp()

# # Extract the zip file to temp directory
# with zipfile.ZipFile(file, 'r') as zip_ref:
#     zip_ref.extractall(temp_dir)

# # Path to media folder
# media_path = os.path.join(temp_dir, 'ppt', 'media')

# # Check if media folder exists
# if os.path.exists(media_path):
#     # Create temporary directory for converted files
#     temp_audio_dir = tempfile.mkdtemp()
    
#     # Iterate through slide numbers
#     slide_num = 1
#     while True:
#         # Check for either .mp4 or .m4a file for current slide
#         media_file = None
#         for ext in ['.mp4', '.m4a']:
#             filename = f'media{slide_num}{ext}'
#             file_path = os.path.join(media_path, filename)
#             if os.path.exists(file_path):
#                 media_file = file_path
#                 break
                
#         if not media_file:
#             break
            
#         # Create temporary mp3 file
#         temp_mp3 = os.path.join(temp_audio_dir, f'temp_{slide_num}.mp3')
        
#         try:
#             # Convert to mp3 using ffmpeg
#             os.system(f'ffmpeg -i "{media_file}" -vn -acodec libmp3lame "{temp_mp3}" -loglevel quiet')
#             # Store the temp mp3 file path in dictionary
#             audio_files[slide_num-1] = temp_mp3
#         except Exception as e:
#             print(f"Error converting slide {slide_num}: {str(e)}")
            
#         slide_num += 1

# # Load Whisper model
# model = whisper.load_model("base")

# # Dictionary to store transcriptions by slide number
# slide_transcripts = {}

# # Transcribe each audio file
# for slide_num, audio_file in audio_files.items():
#     # Transcribe the audio file
#     result = model.transcribe(audio_file)
#     # Store transcription text for this slide
#     slide_transcripts[slide_num + 1] = result["text"]
   

# # Display transcription per slide
# print("\nTranscription by Slide:")
# for slide_num, text in sorted(slide_transcripts.items()):
#     print(f"\nSlide {slide_num}:")
#     print(text)

import streamlit as st
import zipfile
import os
import tempfile
import whisper
from pathlib import Path

def process_pptx(uploaded_file):
    # Create temporary file to save the uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_pptx:
        tmp_pptx.write(uploaded_file.getvalue())
        pptx_path = tmp_pptx.name
    
    # Convert PPTX path to ZIP path
    zip_path = os.path.splitext(pptx_path)[0] + '.zip'
    os.rename(pptx_path, zip_path)
    
    # Create dictionary to store audio files
    audio_files = {}
    
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp()
    
    with st.spinner('Extracting PPTX contents...'):
        # Extract the zip file to temp directory
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    
    # Path to media folder
    media_path = os.path.join(temp_dir, 'ppt', 'media')
    
    # Check if media folder exists
    if os.path.exists(media_path):
        # Create temporary directory for converted files
        temp_audio_dir = tempfile.mkdtemp()
        
        # Progress bar for audio conversion
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # First count total slides with audio
        total_slides = 0
        slide_num = 1
        while True:
            found = False
            for ext in ['.mp4', '.m4a']:
                if os.path.exists(os.path.join(media_path, f'media{slide_num}{ext}')):
                    total_slides += 1
                    found = True
                    break
            if not found:
                break
            slide_num += 1
        
        # Process audio files
        slide_num = 1
        processed_slides = 0
        while True:
            # Check for either .mp4 or .m4a file for current slide
            media_file = None
            for ext in ['.mp4', '.m4a']:
                filename = f'media{slide_num}{ext}'
                file_path = os.path.join(media_path, filename)
                if os.path.exists(file_path):
                    media_file = file_path
                    break
                    
            if not media_file:
                break
                
            # Create temporary mp3 file
            temp_mp3 = os.path.join(temp_audio_dir, f'temp_{slide_num}.mp3')
            
            try:
                status_text.text(f'Converting audio from slide {slide_num}...')
                # Convert to mp3 using ffmpeg
                os.system(f'ffmpeg -i "{media_file}" -vn -acodec libmp3lame "{temp_mp3}" -loglevel quiet')
                # Store the temp mp3 file path in dictionary
                audio_files[slide_num-1] = temp_mp3
                processed_slides += 1
                progress_bar.progress(processed_slides / total_slides)
            except Exception as e:
                st.error(f"Error converting slide {slide_num}: {str(e)}")
                
            slide_num += 1
        
        progress_bar.empty()
        status_text.empty()
        
        # Load Whisper model
        with st.spinner('Loading Whisper model...'):
            model = whisper.load_model("base")
        
        # Dictionary to store transcriptions by slide number
        slide_transcripts = {}
        
        # Progress bar for transcription
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Transcribe each audio file
        for idx, (slide_num, audio_file) in enumerate(audio_files.items()):
            status_text.text(f'Transcribing slide {slide_num + 1}...')
            # Transcribe the audio file
            result = model.transcribe(audio_file)
            # Store transcription text for this slide
            slide_transcripts[slide_num + 1] = result["text"]
            progress_bar.progress((idx + 1) / len(audio_files))
        
        progress_bar.empty()
        status_text.empty()
        
        # Clean up temporary files
        os.unlink(zip_path)
        
        return slide_transcripts
    return None

def main():
    st.title('Audio2Text')
    st.write('Upload a PowerPoint file (PPTX) to transcribe its audio content')
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PPTX file", type="pptx")
    
    if uploaded_file is not None:
        # Check file size (2GB limit)
        if uploaded_file.size > 2 * 1024 * 1024 * 1024:
            st.error("File size exceeds 2GB limit")
            return
            
        st.write("Processing... This may take a while depending on the number and length of audio clips.")
        
        # Process the file
        transcripts = process_pptx(uploaded_file)
        
        if transcripts:
            st.subheader("Transcription Results")
            for slide_num, text in sorted(transcripts.items()):
                st.markdown(f"**Slide {slide_num}**")
                st.write(text)
                st.markdown("---")
        else:
            st.warning("No audio content found in the PowerPoint file.")

if __name__ == "__main__":
    main()