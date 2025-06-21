import openai
import os
import streamlit as st
from typing import List, Optional
import re
from utils.constants import OPENAI_MODEL, IMAGE_SIZE, IMAGE_QUALITY, MAX_KEYWORDS_PER_ANSWER

# 🔑 여기에 OpenAI API 키를 직접 입력하세요
# 예시: OPENAI_API_KEY = "sk-your-api-key-here"
OPENAI_API_KEY = ""  # 여기에 본인의 OpenAI API 키를 입력하세요

class ImageGenerator:
    """이미지 생성 관련 기능을 처리하는 클래스"""
    
    def __init__(self):
        self.client = self._get_openai_client()
    
    def _get_openai_client(self) -> Optional[openai.OpenAI]:
        """OpenAI 클라이언트 초기화"""
        try:
            # 1. 코드에서 직접 설정한 API 키 사용
            api_key = OPENAI_API_KEY
            
            # 2. 코드에 없으면 환경변수에서 확인
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다. 파일 상단의 OPENAI_API_KEY 변수에 API 키를 입력해주세요.")
                return None
                
            return openai.OpenAI(api_key=api_key)
            
        except Exception as e:
            st.error(f"OpenAI API 키 설정 오류: {e}")
            return None
    
    def generate_image(self, keywords: List[str]) -> Optional[str]:
        """키워드를 기반으로 이미지 생성"""
        if not self.client:
            st.error("❌ OpenAI API 클라이언트가 초기화되지 않았습니다. API 키를 확인해주세요.")
            return None
        
        if not keywords:
            st.warning("⚠️ 이미지 생성을 위한 키워드가 없습니다.")
            return None
        
        prompt = self._create_prompt(keywords)
        
        try:
            response = self.client.images.generate(
                model=OPENAI_MODEL,
                prompt=prompt,
                size=IMAGE_SIZE,
                quality=IMAGE_QUALITY,
                n=1,
            )
            
            image_url = response.data[0].url
            print(f"🎨 생성된 이미지 프롬프트: {prompt}")
            return image_url
            
        except openai.RateLimitError:
            st.error("❌ OpenAI API 사용량 한도에 도달했습니다. 잠시 후 다시 시도해주세요.")
            return None
        except openai.AuthenticationError:
            st.error("❌ OpenAI API 키가 유효하지 않습니다. API 키를 확인해주세요.")
            return None
        except Exception as e:
            st.error(f"이미지 생성 중 오류 발생: {e}")
            return None
    
    def _create_prompt(self, keywords: List[str]) -> str:
        """키워드 리스트를 받아서 이미지 생성 프롬프트 생성"""
        if not keywords:
            return "Make a peaceful memory scene."
        
        # 최대 키워드 개수 제한
        limited_keywords = keywords[:MAX_KEYWORDS_PER_ANSWER]
        
        # 키워드를 영어로 번역이 필요할 수 있지만, 일단 그대로 사용
        keyword_string = ", ".join(limited_keywords)
        
        # 요구사항에 맞는 프롬프트 형식: "Make a photo about [키워드들]"
        prompt = f"Make a photo about {keyword_string}."
        
        return prompt

# 싱글톤 패턴으로 이미지 생성기 인스턴스 관리
_image_generator = None

def get_image_generator() -> ImageGenerator:
    """이미지 생성기 싱글톤 인스턴스 반환"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
