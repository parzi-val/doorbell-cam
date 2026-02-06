import os
import json
import time
from google import genai
from google.genai import types
from backend.config.config import Config

class ClipSummarizer:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        if not self.api_key:
            print("[SUMMARIZER] Warning: GEMINI_API_KEY not found in environment.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[SUMMARIZER] Failed to initialize client: {e}")
                self.client = None

    def summarize(self, video_path, metadata):
        """
        Uploads video and generates summary using Gemini 1.5 Flash.
        Returns the summary text or None if failed.
        """
        if not self.client:
            return None

        try:
            print(f"[SUMMARIZER] Uploading {video_path}...")
            # Upload file
            video_file = self.client.files.upload(file=video_path)
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                print("[SUMMARIZER] Waiting for video processing...")
                time.sleep(2)
                video_file = self.client.files.get(name=video_file.name)
                
            if video_file.state.name == "FAILED":
                print("[SUMMARIZER] Video processing failed.")
                return None
                
            print(f"[SUMMARIZER] Generating summary context...")
            
            # Construct Prompt
            # We can inject signal stats to help the model focus
            max_intent = metadata.get("max_intent", 0)
            weapon = metadata.get("weapon_detected", False)
            trigger = metadata.get("trigger_level", "Unknown")
            
            prompt = f"""
            Analyze this security camera footage. 
            Context:
            - Trigger Event: {trigger}
            - Max Intent Score: {max_intent:.2f} (Scale 0-1)
            - Weapon Detected: {weapon}
            
            Please provide a concise summary of the event. Focus on:
            1. What caused the trigger?
            2. Describe the person's behavior and intent cues.
            3. Did they show any aggression or holding any objects?
            4. Is this a genuine threat or false alarm?
            
            Output as a single paragraph.
            """
            
            # Generate content
            # model="gemini-1.5-flash-002"
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    video_file,
                    prompt
                ]
            )
            
            print("[SUMMARIZER] Summary generated.")
            return response.text

        except Exception as e:
            print(f"[SUMMARIZER] Error: {e}")
            return None
