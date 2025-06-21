#!/usr/bin/env python3
"""
기억 점검 관련 유틸리티 함수들
"""

from typing import List, Tuple, Dict
import re
from datetime import date

# 이 파일이 앱의 일부로 임포트될 때 상수를 사용할 수 있도록 가져옵니다.
try:
    from utils.constants import KEYWORD_MATCH_THRESHOLD
except ImportError:
    # 만약 단독으로 사용되거나 경로 문제가 있을 경우를 대비한 기본값
    KEYWORD_MATCH_THRESHOLD = 3

class MemoryChecker:
    """기억 검증 관련 기능을 처리하는 클래스"""
    
    def __init__(self, keyword_threshold: int = KEYWORD_MATCH_THRESHOLD):
        """
        초기화 메서드.
        Args:
            keyword_threshold (int): 기억 검증 통과를 위한 최소 키워드 일치 개수.
        """
        self.keyword_threshold = keyword_threshold
    
    @staticmethod
    def get_days_since_diagnosis(diagnosis_date: date) -> int:
        """진단일로부터 경과한 일수를 계산합니다."""
        if not diagnosis_date:
            return 0
        return (date.today() - diagnosis_date).days

    def verify_memory_by_keywords(self, original_keywords: List[str], recall_text: str) -> Tuple[bool, int]:
        """
        기억 검증을 수행합니다. (키워드 포함 여부로만 확인)
        
        Args:
            original_keywords: 원본 답변에서 추출된 키워드 리스트.
            recall_text: 사용자가 회상하여 입력한 답변 텍스트.
            
        Returns:
            Tuple[bool, int]: (통과 여부, 매칭된 키워드 개수)
        """
        if not original_keywords or not recall_text:
            return False, 0
        
        keyword_match_count = self.count_keyword_matches(original_keywords, recall_text)
        is_passed = keyword_match_count >= self.keyword_threshold
        
        return is_passed, keyword_match_count
    
    def count_keyword_matches(self, keywords: List[str], text: str) -> int:
        """
        주어진 텍스트에 키워드 리스트의 단어가 몇 개 포함되는지 계산합니다.
        
        Args:
            keywords: 확인할 키워드 리스트.
            text: 검사 대상 텍스트.
            
        Returns:
            int: 텍스트에 포함된 키워드의 총 개수.
        """
        if not keywords or not text:
            return 0
        
        text_lower = text.lower()
        match_count = 0
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                match_count += 1
        
        return match_count
    
    def get_keyword_match_details(self, keywords: List[str], text: str) -> Dict[str, bool]:
        """
        각 키워드가 텍스트에 포함되었는지 여부를 상세히 반환합니다.
        (내부 기록 및 분석용으로 사용될 수 있습니다.)
        
        Args:
            keywords: 확인할 키워드 리스트.
            text: 검사 대상 텍스트.
            
        Returns:
            Dict[str, bool]: 각 키워드별 포함 여부를 나타내는 딕셔너리.
        """
        if not keywords or not text:
            return {}
        
        text_lower = text.lower()
        match_details = {}
        
        for keyword in keywords:
            match_details[keyword] = keyword.lower() in text_lower
        
        return match_details
        
    def calculate_memory_score(self, original_keywords: List[str], recall_text: str) -> Dict[str, float]:
        """
        기억 점수를 계산하여 상세 정보를 반환합니다.
        (내부 기록 및 분석용으로 사용될 수 있습니다.)
        
        Args:
            original_keywords: 원본 키워드 리스트.
            recall_text: 회상한 텍스트.
            
        Returns:
            Dict[str, float]: 점수 관련 상세 정보.
        """
        if not original_keywords:
            return {
                'keyword_score': 0.0,
                'match_count': 0,
                'total_keywords': 0,
                'match_rate': 0.0
            }

        if not recall_text:
             return {
                'keyword_score': 0.0,
                'match_count': 0,
                'total_keywords': len(original_keywords),
                'match_rate': 0.0
            }

        match_count = self.count_keyword_matches(original_keywords, recall_text)
        total_keywords = len(original_keywords)
        match_rate = match_count / total_keywords if total_keywords > 0 else 0.0
        
        # 키워드 점수 (0~100)
        keyword_score = match_rate * 100
        
        return {
            'keyword_score': keyword_score,
            'match_count': match_count,
            'total_keywords': total_keywords,
            'match_rate': match_rate
        }