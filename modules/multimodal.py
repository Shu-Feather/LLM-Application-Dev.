import os
import base64
import openai
import whisper
from PIL import Image

class MultiModalProcessor:
    def __init__(self, whisper_model_name: str = os.getenv('WHISPER_MODEL', 'base')):
        try:
            self.whisper_model = whisper.load_model(whisper_model_name)
        except Exception:
            self.whisper_model = None

    def image_to_base64(self, image_path: str) -> str:
        """Convert an image file to a Base64-encoded string."""
        with open(image_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')

    def process_image_input(self, image_path: str) -> str:
        """Process an image file and generate a description using OpenAI's vision-capable model."""
        if not os.path.exists(image_path):
            return f"[Error] Image path not found: {image_path}"
        
        # Convert the image to Base64
        b64 = self.image_to_base64(image_path)
        
        # # Check if the model supports vision (e.g., GPT-4 with vision)
        model = os.getenv('LLM_MODEL', 'gpt-4')
        # if 'gpt-4' not in model or 'vision' not in model:
        #     return "[Error] The specified model does not support vision capabilities."
        
        try:
            # Send the full Base64-encoded image to the API
            resp = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请对以下图片生成简要中文描述。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                        ]
                    }
                ]
            )
            desc = resp.choices[0].message.content.strip()
            return desc
        except Exception as e:
            return f"[Error] Failed to generate image description: {str(e)}"

    def process_audio_input(self, audio_path: str) -> str:
        """Transcribe audio using Whisper model."""
        if self.whisper_model is None:
            return "[Whisper 模型未加载，无法本地转录]"
        if not os.path.exists(audio_path):
            return f"[Error] Audio path not found: {audio_path}"
        try:
            result = self.whisper_model.transcribe(audio_path)
            return result.get('text', '')
        except Exception as e:
            return f"[音频处理失败: {e}]"

    def generate_image(self, prompt: str, n: int = 1, size: str = "512x512") -> list:
        """Generate images using OpenAI's image generation API."""
        try:
            resp = openai.images.generate(
                prompt=prompt,
                n=n,
                size=size
            )
            return [item["url"] for item in resp.data]
        except Exception:
            return []

    def audio_to_speech(self, text: str, output_path: str) -> str:
        """Placeholder for text-to-speech functionality."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return output_path
        except Exception as e:
            return f"[TTS 失败: {e}]"