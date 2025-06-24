import os
import base64
import openai
import whisper
import requests
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class MultiModalProcessor:
    def __init__(self, whisper_model_name: str = os.getenv('WHISPER_MODEL', 'base')):
        try:
            self.whisper_model = whisper.load_model(whisper_model_name)
        except Exception as e:
            logger.warning(f"无法加载Whisper模型: {str(e)}")
            self.whisper_model = None
        
        # 检查API密钥
        if not openai.api_key:
            load_dotenv()
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                logger.error("未设置OPENAI_API_KEY环境变量")

    def image_to_base64(self, image_path: str) -> str:
        """将图像文件转换为Base64编码字符串"""
        try:
            with Image.open(image_path) as img:
                # 调整图像大小以降低API成本
                if max(img.size) > 1024:
                    img.thumbnail((1024, 1024))
                
                # 转换为RGB模式（处理RGBA图像）
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # 保存为JPEG格式（减少文件大小）
                img.save("temp.jpg", "JPEG", quality=85)
                
            with open("temp.jpg", 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode('utf-8')
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            return ""

    def process_image_input(self, image_path: str, model_name: str = None) -> str:
        """处理图像文件并生成描述"""
        if not os.path.exists(image_path):
            return f"[错误] 图像路径不存在: {image_path}"
        
        # 获取支持视觉的模型
        vision_models = ["gpt-4-turbo", "gpt-4o", "gpt-4-vision-preview"]
        model = model_name or os.getenv('LLM_MODEL', 'gpt-4o')
        
        # 检查模型是否支持视觉
        if model not in vision_models:
            logger.warning(f"模型 {model} 不支持视觉功能，请使用以下模型之一: {', '.join(vision_models)}")
            return f"[错误] 模型 {model} 不支持视觉功能"
        
        # 转换图像为Base64
        b64 = self.image_to_base64(image_path)
        if not b64:
            return "[错误] 图像转换失败"
        
        try:
            # 发送到OpenAI API
            resp = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请对以下图片生成详细中文描述，包括场景、对象、颜色、文字内容等所有可见元素。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }
                ],
                max_tokens=1000
            )
            desc = resp.choices[0].message.content.strip()
            return desc
        except openai.APIError as e:
            logger.error(f"API错误: {e.message}")
            return f"[API错误] {e.message}"
        except Exception as e:
            logger.error(f"生成图像描述失败: {str(e)}")
            return f"[错误] 无法生成描述: {str(e)}"

    def process_audio_input(self, audio_path: str) -> str:
        """使用Whisper模型转录音频"""
        if not self.whisper_model:
            return "[错误] Whisper模型未加载"
        if not os.path.exists(audio_path):
            return f"[错误] 音频路径不存在: {audio_path}"
        try:
            # 转换音频格式（如果需要）
            if not audio_path.lower().endswith('.wav'):
                converted_path = "temp_audio.wav"
                self.convert_audio_format(audio_path, converted_path)
                audio_path = converted_path
            
            result = self.whisper_model.transcribe(audio_path)
            return result.get('text', '')
        except Exception as e:
            logger.error(f"音频处理失败: {str(e)}")
            return f"[错误] 音频处理失败: {str(e)}"
    
    def convert_audio_format(self, input_path: str, output_path: str):
        """转换音频格式为WAV"""
        try:
            import subprocess
            subprocess.run([
                "ffmpeg", "-i", input_path, 
                "-acodec", "pcm_s16le", 
                "-ac", "1", 
                "-ar", "16000", 
                output_path
            ], check=True)
        except Exception as e:
            logger.error(f"音频格式转换失败: {str(e)}")
            raise

    def generate_image(self, prompt: str, n: int = 1, size: str = "1024x1024") -> list:
        """使用DALL-E生成图像"""
        try:
            resp = openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=n,
                size=size,
                quality="hd",
                style="vivid"
            )
            return [item.url for item in resp.data]
        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}")
            return []

    def text_to_speech(self, text: str, output_path: str, voice: str = "alloy") -> str:
        """使用OpenAI TTS将文本转换为语音"""
        try:
            response = openai.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            response.stream_to_file(output_path)
            return output_path
        except Exception as e:
            logger.error(f"文本转语音失败: {str(e)}")
            return f"[错误] 文本转语音失败: {str(e)}"