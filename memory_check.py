from difflib import SequenceMatcher
from datetime import date
from typing import Tuple, Optional
import streamlit as st
from keyword_extractor import get_keyword_extractor
from utils.constants import SIMILARITY_THRESHOLD

class MemoryChecker:
    """기억 확인 관련 로직을 처리하는 클래스"""
    # __init__ 메서드 추가
    def __init__(self):
        self.keyword_extractor = get_keyword_extractor()
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """두 텍스트의 유사도를 0-1 사이의 값으로 반환"""
        return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
    
    # @staticmethod
    # def verify_memory(original_answer: str, current_answer: str, 
    #                  threshold: float = SIMILARITY_THRESHOLD) -> Tuple[bool, float]:
    #     """기억 검증 수행"""
    #     similarity = MemoryChecker.calculate_similarity(original_answer, current_answer)
    #     is_passed = similarity >= threshold
    #     return is_passed, similarity
    def verify_memory(self, original_answer: str, current_answer: str, 
                 threshold: float = SIMILARITY_THRESHOLD, 
                 use_keywords: bool = True) -> Tuple[bool, float, Optional[dict]]:
        """기억 검증 수행
        
        Returns:
            (통과 여부, 유사도 점수, 키워드 정보 딕셔너리)
        """
        # 텍스트 유사도 계산
        text_similarity = self.calculate_similarity(original_answer, current_answer)
        
        # 키워드 기반 유사도 계산
        keyword_info = None
        if use_keywords:
            # 원본 답변과 현재 답변에서 키워드 추출
            original_keywords = self.keyword_extractor.extract_keywords(original_answer)
            current_keywords = self.keyword_extractor.extract_keywords(current_answer)
            
            # 키워드 유사도 계산
            keyword_similarity = self.keyword_extractor.calculate_keyword_similarity(
                original_keywords, current_keywords
            )
            
            # 일치하는 키워드 찾기
            matching, only_original, only_current = self.keyword_extractor.get_matching_keywords(
                original_keywords, current_keywords
            )
            
            keyword_info = {
                'original_keywords': original_keywords,
                'current_keywords': current_keywords,
                'keyword_similarity': keyword_similarity,
                'matching_keywords': matching,
                'missing_keywords': only_original,
                'new_keywords': only_current
            }
            
            # 가중 평균 계산 (텍스트 50%, 키워드 50%)
            combined_similarity = (text_similarity * 0.5) + (keyword_similarity * 0.5)
            
        else:
            combined_similarity = text_similarity
        
        is_passed = combined_similarity >= threshold
        return is_passed, combined_similarity, keyword_info

    @staticmethod
    def get_days_since_diagnosis(diagnosis_date: date) -> int:
        """진단일로부터 경과한 일수 계산"""
        return (date.today() - diagnosis_date).days
    
    @staticmethod
    def determine_mode_by_diagnosis(diagnosis_date: date, initial_phase_days: int = 30) -> str:
        """진단일 기준으로 현재 모드 결정"""
        days_passed = MemoryChecker.get_days_since_diagnosis(diagnosis_date)
        if days_passed < initial_phase_days:
            return 'initial_phase'
        else:
            return 'memory_check_phase'