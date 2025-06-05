from difflib import SequenceMatcher
from datetime import date
from typing import Tuple, Optional
import streamlit as st
from utils.constants import SIMILARITY_THRESHOLD

class MemoryChecker:
    """기억 확인 관련 로직을 처리하는 클래스"""
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """두 텍스트의 유사도를 0-1 사이의 값으로 반환"""
        return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
    
    @staticmethod
    def verify_memory(original_answer: str, current_answer: str, 
                     threshold: float = SIMILARITY_THRESHOLD) -> Tuple[bool, float]:
        """기억 검증 수행"""
        similarity = MemoryChecker.calculate_similarity(original_answer, current_answer)
        is_passed = similarity >= threshold
        return is_passed, similarity
    
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