#!/usr/bin/env python3
"""
개선된 4단계: KLUE-BERT 키워드 추출 모델 학습
- 매번 초기화 및 새로운 파일명으로 저장
- 이전 학습 데이터 자동 정리
"""

import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_recall_fscore_support
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import glob
import re
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import os
import shutil
from datetime import datetime

def cleanup_previous_training():
    """이전 학습 결과 정리"""
    print("🧹 이전 학습 결과 정리 중...")
    
    # 삭제할 파일/폴더 패턴들
    patterns_to_clean = [
        "best_model*.pt",
        "training_history*.png", 
        "klue_keyword_extractor*",
        "*.pt"  # 모든 PyTorch 모델 파일
    ]
    
    cleaned_count = 0
    
    for pattern in patterns_to_clean:
        files = glob.glob(pattern)
        for file_path in files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"   🗑️ 파일 삭제: {file_path}")
                    cleaned_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"   🗑️ 폴더 삭제: {file_path}")
                    cleaned_count += 1
            except Exception as e:
                print(f"   ⚠️ 삭제 실패 {file_path}: {e}")
    
    if cleaned_count > 0:
        print(f"✅ {cleaned_count}개 파일/폴더 정리 완료")
    else:
        print("✅ 정리할 파일 없음")

def generate_timestamp_suffix():
    """타임스탬프 기반 파일명 생성"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def load_labeled_data():
    """라벨링된 KLUE 데이터 로드 및 확장""" # <<< 주석 변경
    print("📂 라벨링된 KLUE 데이터 로드 중...")
    
    # 라벨링된 KLUE 파일들 찾기
    labeled_files = glob.glob("KLUE_tokenized_answers*_labeled.json")
    
    # 파일이 없으면 빈 리스트를 반환하고 함수 종료
    if not labeled_files:
        print("❌ KLUE_tokenized_answers*_labeled.json 파일을 찾을 수 없습니다.")
        return []

    print(f"✅ 발견된 라벨링 파일: {len(labeled_files)}개")
    
    all_labeled_data = []
    total_samples = 0
    total_keywords = 0
    
    # 기존과 동일: 모든 JSON 파일에서 데이터를 읽어 all_labeled_data에 추가
    for file_path in sorted(labeled_files):
        print(f"📄 로딩 중: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                samples = json.load(f)
            
            file_keywords = 0
            valid_samples = []
            
            for sample in samples:
                # (데이터 유효성 검사 로직은 그대로 유지)
                if not all(key in sample for key in ["tokens", "labels", "input_ids", "attention_mask"]):
                    continue
                if len(sample["tokens"]) != len(sample["labels"]):
                    continue
                valid_labels = {"O", "B-KEY", "I-KEY"}
                if not all(label in valid_labels for label in sample["labels"]):
                    continue
                
                keyword_count = sum(1 for label in sample["labels"] if label.startswith('B-'))
                file_keywords += keyword_count
                
                sample["keyword_count"] = keyword_count
                sample["labeled"] = True
                
                valid_samples.append(sample)
            
            all_labeled_data.extend(valid_samples)
            total_keywords += file_keywords
            # total_samples는 나중에 한번에 계산하므로 여기서 제외
            
            print(f"   ✅ {len(valid_samples)}개 유효 샘플, {file_keywords}개 키워드")
            
        except Exception as e:
            print(f"   ❌ {file_path} 로드 실패: {e}")
            continue
            
    # <<< 이 아래에 데이터 확장 로직을 추가합니다 >>>
    
    # 1. 확장할 목표 데이터 개수 설정
    TARGET_COUNT = 1000
    
    # 2. 불러온 데이터가 있고, 그 수가 목표치보다 적은 경우에만 확장 수행
    if all_labeled_data and len(all_labeled_data) < TARGET_COUNT:
        print(f"\n🔬 원본 데이터 {len(all_labeled_data)}개를 {TARGET_COUNT}개로 확장합니다...")
        
        expanded_data = []
        for i in range(TARGET_COUNT):
            # 원본 데이터를 순환하며 복사
            base_sample = all_labeled_data[i % len(all_labeled_data)]
            sample = base_sample.copy()
            # 필요하다면 복제된 샘플에 고유 ID 부여
            sample["sample_id"] = f"expanded_{i+1}"
            expanded_data.append(sample)
        
        # 확장된 데이터로 기존 리스트를 교체
        all_labeled_data = expanded_data
        print(f"✅ 데이터 확장 완료!")

    # <<< 여기까지 데이터 확장 로직 >>>


    # 이제부터의 모든 통계는 확장된 데이터를 기준으로 계산됩니다.
    total_samples = len(all_labeled_data)
    if total_samples == 0:
        print("\n- 불러온 데이터가 없습니다.")
        return []
        
    total_keywords = sum(s.get("keyword_count", 0) for s in all_labeled_data)
    
    print(f"\n📊 라벨링 데이터 로드 완료:")
    print(f"   총 샘플: {total_samples:,}개")
    print(f"   총 키워드: {total_keywords:,}개")
    if total_samples > 0:
        print(f"   평균 키워드/샘플: {total_keywords/total_samples:.1f}개")
    
    # 라벨 분포 확인
    if all_labeled_data:
        all_labels = [label for sample in all_labeled_data for label in sample["labels"]]
        
        label_counts = pd.Series(all_labels).value_counts()
        print(f"\n📈 라벨 분포:")
        for label, count in label_counts.items():
            print(f"   {label}: {count:,}개 ({count/len(all_labels)*100:.1f}%)")
        
        # 예시 출력
        print(f"\n💡 라벨링 예시 (첫 번째 샘플):")
        # ... (예시 출력 코드는 동일) ...

    return all_labeled_data

''' def create_example_labeled_data():
    """예시 라벨링 데이터 생성 (테스트용)"""
    print("🔧 예시 라벨링 데이터 생성 중...")
    
    example_data = [
        {
            "original_answer": "봄에는 가족과 벚꽃 구경을 갔어요",
            "tokens": ["봄", "##에는", "가족", "##과", "벚꽃", "구경", "##을", "갔어요"],
            "labels": ["B-KEY", "I-KEY", "B-KEY", "I-KEY", "B-KEY", "O", "O", "O"],  # 수정된 라벨링
            "input_ids": [2, 1234, 5678, 2345, 6789, 3456, 7890, 4567, 3],
            "attention_mask": [1, 1, 1, 1, 1, 1, 1, 1, 1],
            "token_type_ids": [0, 0, 0, 0, 0, 0, 0, 0, 0],
            "keyword_count": 3,
            "labeled": True
        },
        {
            "original_answer": "남편과 함께 병원에 갔습니다",
            "tokens": ["남편", "##과", "함께", "병원", "##에", "갔습니다"],
            "labels": ["B-KEY", "I-KEY", "O", "B-KEY", "I-KEY", "O"],  # 수정된 라벨링
            "input_ids": [2, 8901, 4567, 8901, 2345, 6789, 3],
            "attention_mask": [1, 1, 1, 1, 1, 1, 1],
            "token_type_ids": [0, 0, 0, 0, 0, 0, 0],
            "keyword_count": 2,
            "labeled": True
        },
        {
            "original_answer": "어머니와 시장에서 과일을 샀어요",
            "tokens": ["어머니", "##와", "시장", "##에서", "과일", "##을", "샀어요"],
            "labels": ["B-KEY", "I-KEY", "B-KEY", "I-KEY", "B-KEY", "I-KEY", "O"],  # 수정된 라벨링
            "input_ids": [2, 3456, 7890, 1234, 5678, 9012, 3456, 3],
            "attention_mask": [1, 1, 1, 1, 1, 1, 1, 1],
            "token_type_ids": [0, 0, 0, 0, 0, 0, 0, 0],
            "keyword_count": 3,
            "labeled": True
        }
    ]
    
    # 데이터 확장 (학습에 충분한 양으로)
    expanded_data = []
    for i in range(1000):  # 1000개로 확장
        base_sample = example_data[i % len(example_data)]
        sample = base_sample.copy()
        sample["sample_id"] = i + 1
        expanded_data.append(sample)
    
    print(f"✅ 예시 데이터 생성 완료: {len(expanded_data)}개 샘플")
    return expanded_data
    '''

class KeywordDataset(Dataset):
    """키워드 추출용 데이터셋"""
    
    def __init__(self, samples: List[Dict], max_length: int = 128):
        self.samples = samples
        self.max_length = max_length
        
        # 라벨 매핑 (단순 키워드 추출)
        self.label2id = {"O": 0, "B-KEY": 1, "I-KEY": 2}
        self.id2label = {v: k for k, v in self.label2id.items()}
        
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # 입력 데이터 준비
        input_ids = sample["input_ids"][:self.max_length]
        attention_mask = sample["attention_mask"][:self.max_length] 
        
        # 라벨 변환 (토큰 개수에 맞춤)
        token_labels = sample["labels"]
        # input_ids 길이에 맞춰 라벨 조정 (특수 토큰 고려)
        if len(token_labels) < len(input_ids):
            # 패딩 부분은 -100 (무시)
            labels = [-100] + [self.label2id[label] for label in token_labels] + [-100] * (len(input_ids) - len(token_labels) - 1)
        else:
            labels = [-100] + [self.label2id[label] for label in token_labels[:len(input_ids)-2]] + [-100]
        
        # 최대 길이로 패딩
        padding_length = self.max_length - len(input_ids)
        if padding_length > 0:
            input_ids.extend([0] * padding_length)
            attention_mask.extend([0] * padding_length)
            labels.extend([-100] * padding_length)
        
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long)
        }

class KLUEKeywordExtractor(nn.Module):
    """KLUE-BERT 기반 단순 키워드 추출 모델"""
    
    def __init__(self, model_name: str = "klue/bert-base", num_labels: int = 3, dropout_rate: float = 0.3):
        super().__init__()
        
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)
        
        # 키워드 클래스에 더 높은 가중치 (클래스 불균형 해결)
        self.class_weights = torch.tensor([1.0, 3.0, 2.0])  # O, B-KEY, I-KEY
        
    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        sequence_output = outputs.last_hidden_state
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)
        
        loss = None
        if labels is not None:
            loss_fn = nn.CrossEntropyLoss(
                weight=self.class_weights.to(logits.device), 
                ignore_index=-100
            )
            loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        
        return {"loss": loss, "logits": logits}

def create_data_loaders(labeled_data: List[Dict], test_size: float = 0.2, batch_size: int = 16):
    """데이터 로더 생성"""
    print(f"\n📊 데이터셋 분할 및 데이터 로더 생성...")
    
    # Train/Validation/Test 분할
    train_data, temp_data = train_test_split(labeled_data, test_size=test_size*2, random_state=42)
    val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)
    
    # 데이터셋 생성
    train_dataset = KeywordDataset(train_data)
    val_dataset = KeywordDataset(val_data)
    test_dataset = KeywordDataset(test_data)
    
    # 데이터 로더 생성
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    print(f"✅ 데이터 분할 완료:")
    print(f"   훈련 데이터: {len(train_data):,}개")
    print(f"   검증 데이터: {len(val_data):,}개")
    print(f"   테스트 데이터: {len(test_data):,}개")
    print(f"   배치 크기: {batch_size}")
    
    # 훈련 데이터 라벨 분포 확인
    train_labels = []
    for sample in train_data:
        train_labels.extend(sample["labels"])
    
    label_counts = pd.Series(train_labels).value_counts()
    print(f"\n📈 훈련 데이터 라벨 분포:")
    for label, count in label_counts.items():
        print(f"   {label}: {count:,}개 ({count/len(train_labels)*100:.1f}%)")
    
    return train_loader, val_loader, test_loader, train_dataset.label2id, train_dataset.id2label

def train_model(model, train_loader, val_loader, timestamp, epochs: int = 5, learning_rate: float = 2e-5):
    """모델 학습"""
    print(f"\n🚀 KLUE-BERT 키워드 추출 모델 학습 시작!")
    print(f"   에포크: {epochs}")
    print(f"   학습률: {learning_rate}")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"   사용 장치: {device}")
    
    model.to(device)
    
    # 옵티마이저 및 스케줄러 설정
    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, 
        num_warmup_steps=int(0.1 * total_steps), 
        num_training_steps=total_steps
    )
    
    # 학습 기록
    train_losses = []
    val_f1_scores = []
    best_f1 = 0.0
    best_model_path = f"best_model_{timestamp}.pt"
    
    for epoch in range(epochs):
        print(f"\n📚 에포크 {epoch + 1}/{epochs}")
        
        # 훈련 모드
        model.train()
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        train_bar = tqdm(train_loader, desc=f"훈련 {epoch+1}")
        
        for batch in train_bar:
            # 데이터를 GPU로 이동
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            
            # 그라디언트 초기화
            optimizer.zero_grad()
            
            # 순전파
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs["loss"]
            
            # 역전파
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            
            # 손실 기록
            total_loss += loss.item()
            
            # 예측 결과 저장
            predictions = torch.argmax(outputs["logits"], dim=-1)
            mask = labels != -100
            all_predictions.extend(predictions[mask].cpu().numpy())
            all_labels.extend(labels[mask].cpu().numpy())
            
            train_bar.set_postfix({"Loss": f"{loss.item():.4f}"})
        
        # 에포크 결과
        avg_loss = total_loss / len(train_loader)
        train_f1 = f1_score(all_labels, all_predictions, average='weighted')
        
        train_losses.append(avg_loss)
        
        print(f"   훈련 손실: {avg_loss:.4f}")
        print(f"   훈련 F1: {train_f1:.4f}")
        
        # 검증
        val_f1 = evaluate_model(model, val_loader, device, epoch + 1, "검증")
        val_f1_scores.append(val_f1)
        
        # 최고 성능 모델 저장
        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save(model.state_dict(), best_model_path)
            print(f"   🏆 최고 성능 모델 저장 (F1: {best_f1:.4f}) → {best_model_path}")
    
    print(f"\n🎉 학습 완료! 최고 검증 F1: {best_f1:.4f}")
    return train_losses, val_f1_scores, best_f1, best_model_path

def evaluate_model(model, data_loader, device, epoch=None, data_type="테스트"):
    """모델 평가"""
    model.eval()
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        eval_bar = tqdm(data_loader, desc=f"{data_type} 평가")
        
        for batch in eval_bar:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs["logits"], dim=-1)
            
            mask = labels != -100
            all_predictions.extend(predictions[mask].cpu().numpy())
            all_labels.extend(labels[mask].cpu().numpy())
    
    # 성능 계산
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_predictions, average='weighted', zero_division=0
    )
    
    if epoch:
        print(f"   {data_type} F1: {f1:.4f} (정밀도: {precision:.4f}, 재현율: {recall:.4f})")
    else:
        print(f"\n🔍 최종 {data_type} 평가 결과:")
        print(f"   정밀도: {precision:.4f}")
        print(f"   재현율: {recall:.4f}")
        print(f"   F1 스코어: {f1:.4f}")
        
        # 상세 분류 리포트
        target_names = ["O", "B-KEY", "I-KEY"]
        report = classification_report(
            all_labels, all_predictions, 
            target_names=target_names, 
            zero_division=0
        )
        print(f"\n📊 상세 분류 리포트:")
        print(report)
    
    return f1

def save_model(model, tokenizer, label2id, id2label, timestamp, save_path_base: str = "klue_keyword_extractor"):
    """모델 및 설정 저장"""
    save_path = f"{save_path_base}_{timestamp}"
    print(f"\n💾 모델 저장 중: {save_path}")
    
    try:
        os.makedirs(save_path, exist_ok=True)
        
        # 모델 가중치 직접 저장 (save_pretrained 대신)
        torch.save(model.state_dict(), f"{save_path}/pytorch_model.bin")
        
        # 토크나이저 저장
        tokenizer.save_pretrained(save_path)
        
        # 설정 정보 저장
        config = {
            "model_type": "klue_keyword_extractor",
            "base_model": "klue/bert-base",
            "num_labels": 3,
            "label2id": label2id,
            "id2label": id2label,
            "task": "keyword_extraction",
            "domain": "dementia_patient_answers",
            "labeling_scheme": "BIO",
            "classes": ["O", "B-KEY", "I-KEY"],
            "training_timestamp": timestamp,
            "created_at": datetime.now().isoformat()
        }
        
        with open(f"{save_path}/training_config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 모델 저장 완료!")
        print(f"   모델 경로: {save_path}/")
        print(f"   설정 파일: {save_path}/training_config.json")
        
    except Exception as e:
        print(f"❌ 모델 저장 실패: {e}")

def test_inference(model, tokenizer, test_texts: List[str], device, id2label):
    """실제 추론 테스트 (키워드 최대 6개 추출 제한)""" # <<< 주석 수정
    print(f"\n🧪 추론 테스트 (최대 6개 키워드)") # <<< 출력 메시지 수정
    print("=" * 50)
    
    model.eval()
    
    for i, text in enumerate(test_texts):
        print(f"\n테스트 {i+1}: {text}")
        
        # 토크나이징
        encoding = tokenizer(
            text, 
            return_tensors='pt', 
            truncation=True, 
            padding=True,
            max_length=128
        )
        tokens = tokenizer.tokenize(text)
        
        # 예측
        with torch.no_grad():
            input_ids = encoding['input_ids'].to(device)
            attention_mask = encoding['attention_mask'].to(device)
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs['logits'], dim=-1)
        
        # 결과 처리 (특수 토큰 제외)
        pred_labels = [id2label[pred.item()] for pred in predictions[0][1:len(tokens)+1]]
        
        print("키워드 추출 결과:")
        keywords_found = []
        current_keyword = ""
        
        # <<< 수정된 부분 시작 >>>
        MAX_KEYWORDS = 6 # 최대 키워드 개수 설정

        for token, label in zip(tokens, pred_labels):
            # 이미 6개의 키워드를 찾았으면 루프 중단
            if len(keywords_found) >= MAX_KEYWORDS:
                break

            clean_token = token.replace('##', '')
            
            if label == 'B-KEY':
                if current_keyword: # 이전 키워드 완료
                    keywords_found.append(current_keyword)
                    # 추가 후 키워드 개수 확인
                    if len(keywords_found) >= MAX_KEYWORDS:
                        current_keyword = "" # 더 이상 새 키워드 만들지 않음
                        break

                current_keyword = clean_token
                print(f"  🔑 {token} -> {label}")

            elif label == 'I-KEY' and current_keyword:
                current_keyword += clean_token
                print(f"  ↳ {token} -> {label}")
            else:
                if current_keyword: # 키워드 완료
                    keywords_found.append(current_keyword)
                    current_keyword = ""
        
        # 루프가 끝난 후 마지막 키워드 처리
        if current_keyword and len(keywords_found) < MAX_KEYWORDS:
            keywords_found.append(current_keyword)
        # <<< 수정된 부분 끝 >>>
        
        print(f"🎯 추출된 키워드: {keywords_found}")

# def test_inference(model, tokenizer, test_texts: List[str], device, id2label):
#     """실제 추론 테스트"""
#     print(f"\n🧪 추론 테스트")
#     print("=" * 50)
    
#     model.eval()
    
#     for i, text in enumerate(test_texts):
#         print(f"\n테스트 {i+1}: {text}")
        
#         # 토크나이징
#         encoding = tokenizer(
#             text, 
#             return_tensors='pt', 
#             truncation=True, 
#             padding=True,
#             max_length=128
#         )
#         tokens = tokenizer.tokenize(text)
        
#         # 예측
#         with torch.no_grad():
#             input_ids = encoding['input_ids'].to(device)
#             attention_mask = encoding['attention_mask'].to(device)
            
#             outputs = model(input_ids=input_ids, attention_mask=attention_mask)
#             predictions = torch.argmax(outputs['logits'], dim=-1)
        
#         # 결과 처리 (특수 토큰 제외)
#         pred_labels = [id2label[pred.item()] for pred in predictions[0][1:len(tokens)+1]]
        
#         print("키워드 추출 결과:")
#         keywords_found = []
#         current_keyword = ""
        
#         for token, label in zip(tokens, pred_labels):
#             clean_token = token.replace('##', '')
            
#             if label == 'B-KEY':
#                 if current_keyword:  # 이전 키워드 완료
#                     keywords_found.append(current_keyword)
#                 current_keyword = clean_token
#                 print(f"  🔑 {token} -> {label}")
#             elif label == 'I-KEY' and current_keyword:
#                 current_keyword += clean_token
#                 print(f"  ↳ {token} -> {label}")
#             else:
#                 if current_keyword:  # 키워드 완료
#                     keywords_found.append(current_keyword)
#                     current_keyword = ""
        
#         if current_keyword:  # 마지막 키워드 처리
#             keywords_found.append(current_keyword)
        
#         print(f"🎯 추출된 키워드: {keywords_found}")

def plot_training_history(train_losses, val_f1_scores, timestamp):
    """학습 히스토리 시각화"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # 손실 그래프
    ax1.plot(train_losses, 'b-', label='Training Loss')
    ax1.set_title('Training Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True)
    
    # F1 스코어 그래프
    ax2.plot(val_f1_scores, 'r-', label='Validation F1')
    ax2.set_title('Validation F1 Score')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('F1 Score')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    # 타임스탬프 포함한 파일명
    history_filename = f'training_history_{timestamp}.png'
    plt.savefig(history_filename, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📊 학습 히스토리 그래프 저장: {history_filename}")

def main():
    """개선된 4단계 메인 실행 함수"""
    print("🎯 개선된 4단계: KLUE-BERT 키워드 추출 모델 학습")
    print("=" * 60)
    print("라벨링된 데이터를 사용하여 단순 키워드 추출 모델 학습")
    print("라벨 체계: O (비키워드), B-KEY (키워드 시작), I-KEY (키워드 내부)")
    print("=" * 60)
    
    # 0. 이전 학습 결과 정리
    cleanup_previous_training()
    
    # 타임스탬프 생성
    timestamp = generate_timestamp_suffix()
    print(f"\n🕐 학습 세션 ID: {timestamp}")
    
    # 1. 라벨링된 데이터 로드
    labeled_data = load_labeled_data()
    if not labeled_data:
        return
    
    # 2. 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
    print(f"\n🔧 KLUE-BERT 토크나이저 로드 완료")
    
    # 3. 데이터 로더 생성
    train_loader, val_loader, test_loader, label2id, id2label = create_data_loaders(
        labeled_data, test_size=0.2, batch_size=16
    )
    
    # 4. 모델 생성 (매번 새로 초기화)
    model = KLUEKeywordExtractor(num_labels=3)
    print(f"\n🏗️ KLUE-BERT 키워드 추출 모델 생성 완료 (새로 초기화됨)")
    
    # 5. 모델 학습
    train_losses, val_f1_scores, best_f1, best_model_path = train_model(
        model, train_loader, val_loader, timestamp, epochs=6, learning_rate=2e-5
    )
    
    # 6. 최고 성능 모델 로드
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.load_state_dict(torch.load(best_model_path))
    model.to(device)
    print(f"\n📥 최고 성능 모델 로드: {best_model_path}")
    
    # 7. 최종 평가
    final_f1 = evaluate_model(model, test_loader, device)
    
    # 8. 모델 저장
    save_model(model, tokenizer, label2id, id2label, timestamp)
    
    # 9. 추론 테스트
    test_texts = [
        "대학에서 처음으로 컴퓨터를 사용해 보았던 기억이 있어요. 신기하고 어색했어요.",
        "자식들이 대학에 합격한 순간을 잊지 못해요. 서로를 끌어안고 펑펑 울었던 것 같아요.", 
        "남편이 연락을 받으면 꼭 청혼해야 겠다는 마음으로 연락했어요. 다행이 청혼에 성공하고 결혼까지 했네요.",
        "삶이 힘들어도 다시 일어설 용기가 필요하다는걸 아이들에게 항상 강조해줬던 것 같아요."
    ]
    test_inference(model, tokenizer, test_texts, device, id2label)
    
    # 10. 학습 히스토리 시각화
    plot_training_history(train_losses, val_f1_scores, timestamp)
    
    # 11. 완료 보고서
    print(f"\n🎉 개선된 4단계 완료 보고서")
    print("=" * 40)
    print(f"🕐 학습 세션 ID: {timestamp}")
    print(f"✅ 훈련 데이터: {len(labeled_data):,}개")
    print(f"✅ 최고 검증 F1: {best_f1:.4f}")
    print(f"✅ 최종 테스트 F1: {final_f1:.4f}")
    print(f"✅ 모델 저장: klue_keyword_extractor_{timestamp}/")
    print(f"✅ 최고 모델 파일: {best_model_path}")
    print(f"✅ 학습 곡선: training_history_{timestamp}.png")
    print(f"✅ 라벨 체계: 3개 클래스 (O, B-KEY, I-KEY)")
    
    print(f"\n📋 다음 단계:")
    print(f"1. 실제 서비스에 모델 통합")
    print(f"2. 더 많은 라벨링 데이터로 성능 개선")
    print(f"3. 모델 최적화 및 경량화")
    print(f"4. 라벨링 품질 검증 및 개선")
    
    print(f"\n💾 생성된 파일들:")
    print(f"   📁 klue_keyword_extractor_{timestamp}/")
    print(f"   🏆 {best_model_path}")
    print(f"   📊 training_history_{timestamp}.png")
    
    return model, tokenizer, final_f1, timestamp

if __name__ == "__main__":
    main()
    
