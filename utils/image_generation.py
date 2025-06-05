import openai
import os
import streamlit as st
from typing import List, Optional
import re
from utils.constants import OPENAI_MODEL, IMAGE_SIZE, IMAGE_QUALITY, MAX_KEYWORDS_PER_ANSWER

# 🔑 여기에 OpenAI API 키를 직접 입력하세요
# 예시: OPENAI_API_KEY = "sk-your-api-key-here"
OPENAI_API_KEY = "여기에 OpenAI API 키를 입력"

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
        
        prompt = self._create_prompt(keywords)
        
        try:
            response = self.client.images.generate(
                model=OPENAI_MODEL,
                prompt=prompt,
                size=IMAGE_SIZE,
                quality=IMAGE_QUALITY,
                n=1,
            )
            
            return response.data[0].url
            
        except Exception as e:
            st.error(f"이미지 생성 중 오류 발생: {e}")
            return None
    
    def _create_prompt(self, keywords: List[str]) -> str:
        """키워드 리스트를 받아서 이미지 생성 프롬프트 생성"""
        if not keywords:
            return "Make an image of a peaceful memory scene."
        
        keyword_string = ", ".join(keywords)
        return f"Make an image of {keyword_string}."
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = MAX_KEYWORDS_PER_ANSWER) -> List[str]:
        """텍스트에서 간단한 키워드 추출 (임시 함수)"""
        # 특수문자 제거하고 단어 분리
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 간단한 불용어 제거
        stop_words = {
            '은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', 
            '그', '저', '이런', '그런', '했습니다', '했어요', '해요', 
            '입니다', '있습니다', '있어요', '좋았습니다', '좋았어요'
        }
        
        # 길이 2 이상인 단어만 선택하고 불용어 제거
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
        
        # 중복 제거하고 최대 개수만큼 반환
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:max_keywords]
