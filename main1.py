import whisper
import streamlit as st
import ffmpeg
import tempfile
import os
import subprocess
import re

def extract_audio(input_file, output_file):
    """Extract audio from video file"""
    try:
        # Configure ffmpeg to extract audio
        stream = (
            ffmpeg
            .input(input_file)
            .output(output_file, acodec='libmp3lame', loglevel='quiet')
            .overwrite_output()
        )
        # Run ffmpeg command
        ffmpeg.run(stream)
        return True
    except ffmpeg.Error as e:
        st.error(f"FFmpeg error: {e.stderr.decode()}")
        return False

def detect_scenes_ffmpeg(video_path, threshold=0.2):
    """
    Use FFmpeg's built-in scene detection to get timestamps where scenes (slides) change.
    
    Args:
        video_path (str): Path to the video file.
        threshold (float): Scene change threshold (e.g., 0.4). Lower values are more sensitive.
        
    Returns:
        List of timestamps (floats) in seconds where a scene change was detected.
    """
    # Build the ffmpeg command.
    command = [
        'ffmpeg',
        '-i', video_path,
        '-filter_complex', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null',
        '-'
    ]
    
    # Run the command and capture stderr (scene detection info is printed there)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr_output = result.stderr

    # Use regex to find all occurrences of pts_time in the output
    # Example line in stderr: "... pts_time:12.345 ..."
    pattern = r"pts_time:(\d+\.\d+)"
    times = re.findall(pattern, stderr_output)
    # Convert to float and sort
    scene_times = sorted([float(t) for t in times])
    
    # Optionally, ensure that the first scene starts at 0.0
    if not scene_times or scene_times[0] != 0.0:
        scene_times.insert(0, 0.0)
    
    return scene_times

def map_segments_to_scenes(segments, scene_times, video_duration):
    """
    Map Whisper transcription segments to scenes (slides) based on their timestamps.
    
    Args:
        segments (list): List of transcription segments from Whisper (each containing 'start' and 'text').
        scene_times (list): List of scene change timestamps (in seconds).
        video_duration (float): Total duration of the video.
        
    Returns:
        Dictionary mapping slide numbers (starting at 1) to concatenated transcript text.
    """
    # Make sure scene_times includes 0.0 and the video duration as boundaries
    boundaries = scene_times.copy()
    if boundaries[0] != 0.0:
        boundaries.insert(0, 0.0)
    if boundaries[-1] < video_duration:
        boundaries.append(video_duration)
    
    slide_transcripts = {}
    # Initialize transcript for each slide
    for i in range(len(boundaries) - 1):
        slide_transcripts[i+1] = ""
    
    # Assign each segment to the appropriate slide by its start time
    for seg in segments:
        seg_start = seg["start"]
        # Find which interval (slide) this segment belongs to.
        for i in range(len(boundaries) - 1):
            if boundaries[i] <= seg_start < boundaries[i+1]:
                slide_transcripts[i+1] += seg["text"] + " "
                break
                
    return slide_transcripts

# --- Streamlit App ---
st.title("Video Transcription App")

# File uploader
uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov'])

if uploaded_file is not None:
    try:
        with st.spinner('Processing video...'):
            # Save the uploaded video to a temporary file
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_video.write(uploaded_file.read())
            temp_video.close()
            
            # Create a temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_audio.close()
            
            # Extract audio from video
            if extract_audio(temp_video.name, temp_audio.name):
                # Load Whisper model and transcribe the audio with segments (which include timestamps)
                model = whisper.load_model("base")
                result = model.transcribe(temp_audio.name)
                
                # Get the transcription segments
                segments = result.get("segments", [])
                
                # Determine the video duration (approximate using the last segment's end time)
                if segments:
                    video_duration = segments[-1]["end"]
                else:
                    video_duration = 0.0
                
                # Use FFmpeg to detect scene changes (which we treat as slide changes)
                scene_times = detect_scenes_ffmpeg(temp_video.name, threshold=0.4)
                
                # Map transcription segments to the detected scenes
                slide_transcripts = map_segments_to_scenes(segments, scene_times, video_duration)
                
                # Display the overall transcription
                # st.subheader("Full Transcription:")
                # st.write(result["text"])
                
                # Display transcription per slide
                st.subheader("Transcription by Slide:")
                for slide_num, text in slide_transcripts.items():
                    st.write(f"**Slide {slide_num}:**")
                    st.write(text.strip())
                
                # Add download button for full transcription
                st.download_button(
                    label="Download Full Transcription",
                    data=result["text"],
                    file_name="transcription.txt",
                    mime="text/plain"
                )
            
            # Cleanup temporary files
            os.unlink(temp_video.name)
            os.unlink(temp_audio.name)
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
