#!/usr/bin/env python3
"""
KLUE-BERT 기반 키워드 추출기
훈련된 모델을 로드하고 텍스트에서 키워드를 추출하는 클래스
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import json
import glob
import os
from typing import List, Optional, Dict, Tuple
import streamlit as st

class KLUEKeywordExtractorModel(nn.Module):
    """KLUE-BERT 기반 키워드 추출 모델 (improved_klue_training_keywordLimit.py와 동일)"""
    
    def __init__(self, model_name: str = "klue/bert-base", num_labels: int = 3, dropout_rate: float = 0.3):
        super().__init__()
        
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)
        
    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        sequence_output = outputs.last_hidden_state
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)
        
        loss = None
        if labels is not None:
            loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
            loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        
        return {"loss": loss, "logits": logits}

class KeywordExtractor:
    """키워드 추출기 클래스"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: 모델 경로. None이면 최신 모델 자동 검색
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.label2id = None
        self.id2label = None
        self.max_keywords = 6  # 최대 키워드 개수
        
        # 모델 로드
        self.load_model(model_path)
    
    def find_latest_model(self) -> Optional[str]:
        """가장 최근에 훈련된 모델 찾기"""
        # klue_keyword_extractor_* 폴더들 찾기
        model_dirs = glob.glob("klue_keyword_extractor_*")
        
        if not model_dirs:
            # best_model_*.pt 파일들 찾기
            model_files = glob.glob("best_model_*.pt")
            if model_files:
                # 가장 최신 파일 선택
                latest_file = max(model_files, key=os.path.getctime)
                return latest_file
            return None
        
        # 가장 최신 폴더 선택
        latest_dir = max(model_dirs, key=os.path.getctime)
        return latest_dir
    
    def load_model(self, model_path: Optional[str] = None):
        """모델 로드"""
        try:
            # 모델 경로 결정
            if model_path is None:
                model_path = self.find_latest_model()
                if model_path is None:
                    st.warning("⚠️ 훈련된 모델을 찾을 수 없습니다. 기본 키워드 추출기를 사용합니다.")
                    return
            
            # 모델 설정 로드
            if os.path.isdir(model_path):
                # 디렉토리인 경우
                config_path = os.path.join(model_path, "training_config.json")
                model_weight_path = os.path.join(model_path, "pytorch_model.bin")
                tokenizer_path = model_path
            else:
                # .pt 파일인 경우 (구버전 호환)
                config_path = None
                model_weight_path = model_path
                tokenizer_path = "klue/bert-base"
            
            # 설정 로드
            if config_path and os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.label2id = config.get("label2id", {"O": 0, "B-KEY": 1, "I-KEY": 2})
                    self.id2label = config.get("id2label", {0: "O", 1: "B-KEY", 2: "I-KEY"})
            else:
                # 기본값 사용
                self.label2id = {"O": 0, "B-KEY": 1, "I-KEY": 2}
                self.id2label = {0: "O", 1: "B-KEY", 2: "I-KEY"}
            
            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            
            # 모델 생성 및 가중치 로드
            self.model = KLUEKeywordExtractorModel(num_labels=len(self.label2id))
            
            if os.path.exists(model_weight_path):
                state_dict = torch.load(model_weight_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.model.to(self.device)
                self.model.eval()
                
                print(f"✅ 모델 로드 완료: {model_path}")
            else:
                st.error(f"❌ 모델 파일을 찾을 수 없습니다: {model_weight_path}")
                self.model = None
                
        except Exception as e:
            st.error(f"❌ 모델 로드 실패: {e}")
            self.model = None
    
    def extract_keywords(self, text: str, max_keywords: Optional[int] = None) -> List[str]:
        """텍스트에서 키워드 추출"""
        if not text or not text.strip():
            return []
        
        # 모델이 없으면 기본 추출기 사용
        if self.model is None or self.tokenizer is None:
            return self._extract_keywords_fallback(text, max_keywords or self.max_keywords)
        
        try:
            # 토크나이징
            encoding = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                padding=True,
                max_length=128
            )
            
            # GPU로 이동
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            # 예측
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                predictions = torch.argmax(outputs['logits'], dim=-1)
            
            # 토큰 가져오기
            tokens = self.tokenizer.tokenize(text)
            
            # 키워드 추출
            keywords = self._extract_keywords_from_predictions(
                tokens, 
                predictions[0][1:len(tokens)+1],  # 특수 토큰 제외
                max_keywords or self.max_keywords
            )
            
            return keywords
            
        except Exception as e:
            st.warning(f"⚠️ 모델 추론 중 오류 발생: {e}")
            return self._extract_keywords_fallback(text, max_keywords or self.max_keywords)
    
    def _extract_keywords_from_predictions(self, tokens: List[str], predictions: torch.Tensor, 
                                         max_keywords: int) -> List[str]:
        """예측 결과에서 키워드 추출"""
        keywords_found = []
        current_keyword = ""
        
        for token, pred_id in zip(tokens, predictions):
            # 이미 최대 개수만큼 키워드를 찾았으면 중단
            if len(keywords_found) >= max_keywords:
                break
            
            label = self.id2label[pred_id.item()]
            clean_token = token.replace('##', '')
            
            if label == 'B-KEY':
                if current_keyword:  # 이전 키워드 완료
                    keywords_found.append(current_keyword)
                    if len(keywords_found) >= max_keywords:
                        break
                current_keyword = clean_token
                
            elif label == 'I-KEY' and current_keyword:
                current_keyword += clean_token
                
            else:
                if current_keyword:  # 키워드 완료
                    keywords_found.append(current_keyword)
                    current_keyword = ""
        
        # 마지막 키워드 처리
        if current_keyword and len(keywords_found) < max_keywords:
            keywords_found.append(current_keyword)
        
        return keywords_found
    
    def _extract_keywords_fallback(self, text: str, max_keywords: int) -> List[str]:
        """모델이 없을 때 사용하는 기본 키워드 추출 (기존 방식)"""
        import re
        
        # 특수문자 제거하고 단어 분리
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 간단한 불용어 제거
        stop_words = {
            '은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', 
            '그', '저', '이런', '그런', '했습니다', '했어요', '해요', 
            '입니다', '있습니다', '있어요', '좋았습니다', '좋았어요',
            '하고', '하는', '한', '할', '함', '하며', '하면', '하니',
            '그리고', '그래서', '그러나', '하지만', '그런데'
        }
        
        # 길이 2 이상인 단어만 선택하고 불용어 제거
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
        
        # 중복 제거하고 최대 개수만큼 반환
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:max_keywords]
    
    def calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """두 키워드 리스트 간의 유사도 계산 (0~1)"""
        if not keywords1 or not keywords2:
            return 0.0
        
        # 키워드를 소문자로 변환하여 집합으로 만들기
        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)
        
        # Jaccard 유사도 계산
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        similarity = len(intersection) / len(union)
        return similarity
    
    def get_matching_keywords(self, keywords1: List[str], keywords2: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """두 키워드 리스트 비교하여 일치/불일치 키워드 반환
        
        Returns:
            (일치하는 키워드, keywords1에만 있는 키워드, keywords2에만 있는 키워드)
        """
        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)
        
        matching = list(set1.intersection(set2))
        only_in_1 = list(set1 - set2)
        only_in_2 = list(set2 - set1)
        
        return matching, only_in_1, only_in_2

# 싱글톤 인스턴스
_keyword_extractor = None

def get_keyword_extractor() -> KeywordExtractor:
    """키워드 추출기 싱글톤 인스턴스 반환"""
    global _keyword_extractor
    if _keyword_extractor is None:
        _keyword_extractor = KeywordExtractor()
    return _keyword_extractor