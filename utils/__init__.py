#!/usr/bin/env python3
"""
치매 증상 지연 서비스 - 유틸리티 패키지

이 패키지는 치매 증상 지연 서비스에 필요한 다양한 유틸리티 함수들을 포함합니다.
"""

from .constants import *
from .memory_check import MemoryChecker

__version__ = "1.0.0"
__author__ = "치매 증상 지연 서비스 개발팀"

# 패키지 레벨에서 사용할 수 있는 주요 클래스들
__all__ = [
    # 상수들
    'INITIAL_PHASE_DAYS',
    'MAX_DAILY_NEW_QUESTIONS_INITIAL', 
    'MAX_DAILY_NEW_QUESTIONS_MAINTENANCE',
    'MAX_DAILY_MEMORY_CHECKS',
    'MAX_KEYWORDS_PER_ANSWER',
    'KEYWORD_MATCH_THRESHOLD',
    'SIMILARITY_THRESHOLD',
    
    # 클래스들
    'MemoryChecker',
    'MemoryHintGenerator',
]