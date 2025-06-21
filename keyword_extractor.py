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
from utils.constants import MAX_KEYWORDS_PER_ANSWER

class KeywordBERTModel(nn.Module):
    """KLUE-BERT 기반 키워드 추출 모델"""
    
    def __init__(self, num_labels=3, dropout_rate=0.1):
        super().__init__()
        self.bert = AutoModel.from_pretrained("klue/bert-base")
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)
        
    def forward(self, input_ids=None, attention_mask=None, token_type_ids=None, labels=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        sequence_output = outputs.last_hidden_state
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)
        
        result = {"logits": logits}
        
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
            result["loss"] = loss
            
        return result

# 기존 훈련된 모델이 있으므로 모델 아키텍처 재정의 불필요
# .pt 파일에서 직접 로드하여 사용

class KeywordExtractor:
    """키워드 추출기 클래스 (비상 플랜 로직 제거)"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: 모델 경로. None이면 최신 모델 자동 검색
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.label2id = {"O": 0, "B-KEY": 1, "I-KEY": 2}
        self.id2label = {v: k for k, v in self.label2id.items()}
        self.max_keywords = MAX_KEYWORDS_PER_ANSWER
        
        # 모델 로드 (실패 시 예외 발생)
        self.load_model(model_path)
    
    def find_latest_model(self) -> str:
        """가장 최근에 훈련된 모델 찾기. 없으면 FileNotFoundError 발생"""
        # klue_keyword_extractor_* 폴더들 찾기
        model_dirs = glob.glob("klue_keyword_extractor_*")
        
        if not model_dirs:
            # best_model_*.pt 파일들 찾기
            model_files = glob.glob("best_model_*.pt")
            if model_files:
                # 가장 최신 파일 선택
                latest_file = max(model_files, key=os.path.getctime)
                return latest_file
            raise FileNotFoundError("훈련된 모델 디렉토리 또는 파일을 찾을 수 없습니다.")
        
        # 가장 최신 폴더 선택
        latest_dir = max(model_dirs, key=os.path.getctime)
        return latest_dir
   
    def load_model(self, model_path: Optional[str] = None):
        """state_dict(.pt)를 로드하여 모델을 조립합니다."""
        try:
            if model_path is None:
                model_path = self.find_latest_model()
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")

            # --- 여기가 핵심 수정 부분입니다 ---
            # 1. 먼저 모델의 빈 설계도를 준비합니다.
            self.model = KeywordBERTModel(num_labels=len(self.label2id))
            
            # 2. .pt 파일에서 '부품 상자(state_dict)'를 불러옵니다.
            state_dict = torch.load(model_path, map_location=self.device)
            
            # 3. 빈 설계도에 불러온 부품들을 조립합니다.
            self.model.load_state_dict(state_dict)
            
            # 4. 이제 완전한 모델을 평가 모드로 전환하고, 장치로 보냅니다.
            self.model.to(self.device)
            self.model.eval()
            # ------------------------------------
            
            # 토크나이저는 KLUE-BERT 기본 토크나이저 사용
            self.tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
            
            print(f"✅ 모델 로드 및 조립 완료: {model_path}")
                
        except Exception as e:
            print(f"❌ 모델 로드 중 심각한 오류 발생: {e}")
            self.model = None
            raise

    def extract_keywords(self, text: str, max_keywords: Optional[int] = None) -> List[str]:
        """텍스트에서 키워드 추출 (모델 전용)"""
        # 초기화 시점에 모델 로드가 보장되므로, 모델 존재 여부만 확인
        if self.model is None or self.tokenizer is None:
            st.error("키워드 추출 모델이 정상적으로 로드되지 않았습니다.")
            return []

        if not text or not text.strip():
            return []
        
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
            # 추론 과정에서 오류 발생 시, 사용자에게 알리고 빈 리스트 반환
            st.warning(f"⚠️ 모델 추론 중 오류 발생: {e}")
            return []
    
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
    
    # def calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
    #     """두 키워드 리스트 간의 유사도 계산 (0~1)"""
    #     if not keywords1 or not keywords2:
    #         return 0.0
        
    #     set1 = set(k.lower() for k in keywords1)
    #     set2 = set(k.lower() for k in keywords2)
        
    #     intersection = set1.intersection(set2)
    #     union = set1.union(set2)
        
    #     if not union:
    #         return 0.0
        
    #     similarity = len(intersection) / len(union)
    #     return similarity
    
    # def get_matching_keywords(self, keywords1: List[str], keywords2: List[str]) -> Tuple[List[str], List[str], List[str]]:
    #     """두 키워드 리스트 비교하여 일치/불일치 키워드 반환
        
    #     Returns:
    #         (일치하는 키워드, keywords1에만 있는 키워드, keywords2에만 있는 키워드)
    #     """
    #     set1 = set(k.lower() for k in keywords1)
    #     set2 = set(k.lower() for k in keywords2)
        
    #     matching = list(set1.intersection(set2))
    #     only_in_1 = list(set1 - set2)
    #     only_in_2 = list(set2 - set1)
        
    #     return matching, only_in_1, only_in_2

# 싱글톤 인스턴스
_keyword_extractor = None

def get_keyword_extractor() -> Optional[KeywordExtractor]:
    """키워드 추출기 싱글톤 인스턴스 반환. 초기화 실패 시 None 반환."""
    global _keyword_extractor
    if _keyword_extractor is None:
        try:
            # KeywordExtractor 초기화 시도. 실패하면 예외 발생
            _keyword_extractor = KeywordExtractor()
        except Exception as e:
            # 초기화 실패 시 _keyword_extractor는 None으로 유지됨
            st.error(f"키워드 추출기 인스턴스 생성에 실패했습니다: {e}")
            return None
            
    return _keyword_extractor

def test_keyword_extraction():
    """키워드 추출 테스트 함수"""
    st.subheader("🔍 키워드 추출 테스트")
    extractor = get_keyword_extractor()
    
    if extractor is None:
        st.error("키워드 추출기를 초기화할 수 없습니다. 모델 파일을 확인해주세요.")
        return
    
    test_text = st.text_area(
        "테스트할 텍스트를 입력하세요:",
        value="가족들과 갔던 제주도 여행이 가장 기억에 남아요. 해변에서 놀고 유채꽃도 보고 흑돼지도 먹어서 행복했어요.",
        height=100
    )
    
    if st.button("키워드 추출 테스트"):
        if test_text.strip():
            with st.spinner("키워드를 추출하고 있습니다..."):
                keywords = extractor.extract_keywords(test_text.strip())
                
                if keywords:
                    st.success(f"✅ 추출된 키워드: {', '.join(keywords)}")
                else:
                    st.warning("키워드를 추출할 수 없었습니다.")
        else:
            st.warning("텍스트를 입력해주세요.")

if __name__ == "__main__":
    # 직접 실행 시 테스트 모드
    st.title("🔍 키워드 추출기 테스트")
    test_keyword_extraction()