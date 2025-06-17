#!/usr/bin/env python3
"""
2단계: KLUE-BERT로 데이터 재처리
기존 koBERT 데이터를 KLUE-BERT로 변환하고 라벨링 준비
"""

import json
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModel
from typing import List, Dict, Tuple
import glob
import re

def setup_klue_bert():
    """KLUE-BERT 토크나이저와 모델 설정"""
    print("🔄 KLUE-BERT 설정 중...")
    
    try:
        # KLUE-BERT 토크나이저 로드
        tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
        
        # 모델도 로드 (나중에 임베딩 추출용)
        model = AutoModel.from_pretrained("klue/bert-base")
        
        print("✅ KLUE-BERT 로드 완료!")
        print(f"   Vocab 크기: {tokenizer.vocab_size:,}")
        print(f"   특수 토큰: {tokenizer.special_tokens_map}")
        
        return tokenizer, model
        
    except Exception as e:
        print(f"❌ KLUE-BERT 로드 실패: {e}")
        print("💡 해결 방법:")
        print("   pip install transformers torch")
        print("   또는 인터넷 연결 확인")
        return None, None

def find_kobert_files():
    """koBERT 토크나이즈 파일들 자동 검색"""
    import glob
    import os
    
    print("\n🔍 koBERT 토크나이즈 파일 검색 중...")
    
    # tokenized_answers*.json 패턴으로 파일 검색
    pattern = "tokenized_answers*.json"
    files = glob.glob(pattern)
    
    if not files:
        print("❌ tokenized_answers*.json 파일을 찾을 수 없습니다.")
        return []
    
    # 파일명 정렬 (숫자 순서대로)
    def extract_number(filename):
        import re
        match = re.search(r'tokenized_answers(\d+)\.json', filename)
        return int(match.group(1)) if match else 0
    
    files.sort(key=extract_number)
    
    print(f"✅ 발견된 파일: {len(files)}개")
    for i, file in enumerate(files[:5]):  # 처음 5개만 표시
        print(f"   {i+1}. {file}")
    if len(files) > 5:
        print(f"   ... (총 {len(files)}개)")
    
    return files

def load_original_data():
    """기존 데이터 로드 (32개 파일 처리)"""
    print("\n📂 기존 데이터 로드 중...")
    
    # koBERT 파일들 찾기
    kobert_files = find_kobert_files()
    if not kobert_files:
        return [], []
    
    all_original_answers = []
    all_kobert_data = []
    
    for i, file_path in enumerate(kobert_files):
        try:
            print(f"📄 로딩 중: {file_path} ({i+1}/{len(kobert_files)})")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                kobert_data = json.load(f)
            
            # 원본 답변 텍스트 추출
            original_answers = [sample["original_answer"] for sample in kobert_data]
            
            all_original_answers.extend(original_answers)
            all_kobert_data.append({
                "file_path": file_path,
                "data": kobert_data,
                "sample_count": len(kobert_data)
            })
            
            print(f"   ✅ {len(kobert_data)}개 샘플 로드")
            
        except Exception as e:
            print(f"   ❌ {file_path} 로드 실패: {e}")
            continue
    
    print(f"\n📊 전체 로드 결과:")
    print(f"   총 파일 수: {len(all_kobert_data)}")
    print(f"   총 샘플 수: {len(all_original_answers)}")
    
    # 예시 출력
    if all_original_answers:
        print("\n📝 원본 답변 예시:")
        for i, answer in enumerate(all_original_answers[:3]):
            print(f"   {i+1}. {answer}")
    
    return all_original_answers, all_kobert_data

def reprocess_with_klue_bert_batch(tokenizer, kobert_files_data: List[Dict]) -> List[Dict]:
    """KLUE-BERT로 파일별 배치 처리"""
    print(f"\n🔄 KLUE-BERT로 {len(kobert_files_data)}개 파일 배치 처리 중...")
    
    processed_files = []
    total_samples = 0
    
    for file_idx, file_info in enumerate(kobert_files_data):
        file_path = file_info["file_path"]
        kobert_data = file_info["data"]
        sample_count = file_info["sample_count"]
        
        print(f"\n📄 처리 중: {file_path} ({file_idx+1}/{len(kobert_files_data)})")
        print(f"   샘플 수: {sample_count}개")
        
        # 원본 답변 텍스트 추출
        original_answers = [sample["original_answer"] for sample in kobert_data]
        
        # KLUE-BERT로 재처리
        klue_samples = []
        
        for i, text in enumerate(original_answers):
            if (i + 1) % 10 == 0 or i == len(original_answers) - 1:
                print(f"   진행률: {i+1}/{len(original_answers)} ({(i+1)/len(original_answers)*100:.1f}%)")
            
            # KLUE-BERT 토크나이징
            encoding = tokenizer(
                text,
                truncation=True,
                padding='max_length',
                max_length=128,
                return_tensors='pt',
                return_token_type_ids=True,
                return_attention_mask=True
            )
            
            # 토큰 리스트 생성
            tokens = tokenizer.tokenize(text)
            full_tokens = tokenizer.convert_ids_to_tokens(encoding['input_ids'].squeeze().tolist())
            
            # 데이터 구성
            sample = {
                "original_sample_id": kobert_data[i].get("sample_id", i + 1),
                "klue_sample_id": total_samples + i + 1,
                "original_answer": text,
                
                # KLUE-BERT 토크나이징 결과
                "tokens": tokens,
                "full_tokens": full_tokens,
                
                # 모델 입력용 데이터
                "input_ids": encoding['input_ids'].squeeze().tolist(),
                "attention_mask": encoding['attention_mask'].squeeze().tolist(),
                "token_type_ids": encoding['token_type_ids'].squeeze().tolist(),
                
                # 통계 정보
                "token_count": len(tokens),
                "full_token_count": len(full_tokens),
                "char_count": len(text),
                "compression_ratio": len(tokens) / len(text) if text else 0,
                
                # UNK 토큰 분석
                "unk_count": sum(1 for token in tokens if '[UNK]' in token),
                "unk_ratio": sum(1 for token in tokens if '[UNK]' in token) / len(tokens) * 100 if tokens else 0,
                
                # 라벨링 준비
                "labels": ["O"] * len(tokens),
                "labeling_ready": True,
                
                # 메타데이터
                "source_file": file_path,
                "processed_with": "KLUE-BERT"
            }
            
            klue_samples.append(sample)
        
        # 파일별 결과 저장
        file_result = {
            "source_file": file_path,
            "output_file": file_path.replace("tokenized_answers", "KLUE_tokenized_answers"),
            "samples": klue_samples,
            "sample_count": len(klue_samples),
            "avg_tokens": sum(s["token_count"] for s in klue_samples) / len(klue_samples) if klue_samples else 0,
            "avg_unk_ratio": sum(s["unk_ratio"] for s in klue_samples) / len(klue_samples) if klue_samples else 0
        }
        
        processed_files.append(file_result)
        total_samples += len(klue_samples)
        
        print(f"   ✅ 완료: 평균 {file_result['avg_tokens']:.1f} 토큰, UNK {file_result['avg_unk_ratio']:.1f}%")
    
    print(f"\n🎉 전체 배치 처리 완료!")
    print(f"   처리된 파일: {len(processed_files)}개")
    print(f"   총 샘플: {total_samples}개")
    
    return processed_files

def compare_before_after(kobert_data: List[Dict], klue_data: List[Dict]):
    """재처리 전후 비교"""
    print("\n📊 재처리 전후 비교")
    print("=" * 60)
    
    if not kobert_data or not klue_data:
        print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 전체 통계
    kobert_avg_tokens = sum(len(sample["tokens"]) for sample in kobert_data) / len(kobert_data)
    klue_avg_tokens = sum(sample["token_count"] for sample in klue_data) / len(klue_data)
    
    kobert_total_unk = sum(sample["tokens"].count("[UNK]") for sample in kobert_data)
    kobert_total_tokens = sum(len(sample["tokens"]) for sample in kobert_data)
    kobert_unk_ratio = (kobert_total_unk / kobert_total_tokens * 100) if kobert_total_tokens > 0 else 0
    
    klue_total_unk = sum(sample["unk_count"] for sample in klue_data)
    klue_total_tokens = sum(sample["token_count"] for sample in klue_data)
    klue_unk_ratio = (klue_total_unk / klue_total_tokens * 100) if klue_total_tokens > 0 else 0
    
    print(f"{'항목':<15} {'koBERT (기존)':<15} {'KLUE-BERT (신규)':<18} {'개선도':<10}")
    print("-" * 60)
    print(f"{'평균 토큰 수':<15} {kobert_avg_tokens:<15.1f} {klue_avg_tokens:<18.1f} {'-':<10}")
    print(f"{'UNK 토큰 비율':<15} {kobert_unk_ratio:<15.1f}% {klue_unk_ratio:<18.1f}% {(kobert_unk_ratio-klue_unk_ratio):<10.1f}%↓")
    
    # 샘플별 상세 비교 (처음 3개)
    print(f"\n🔍 샘플별 상세 비교:")
    for i in range(min(3, len(kobert_data), len(klue_data))):
        kobert_sample = kobert_data[i]
        klue_sample = klue_data[i]
        
        print(f"\n--- 샘플 {i+1} ---")
        print(f"원본: {klue_sample['original_answer'][:50]}...")
        print(f"koBERT  토큰: {kobert_sample['tokens'][:8]}...")
        print(f"KLUE-BERT 토큰: {klue_sample['tokens'][:8]}...")
        print(f"개선: {len(kobert_sample['tokens'])} → {klue_sample['token_count']} 토큰")

def analyze_labeling_readiness(klue_data: List[Dict]):
    """라벨링 준비 상태 분석"""
    print(f"\n🏷️ 라벨링 준비 상태 분석")
    print("=" * 40)
    
    total_samples = len(klue_data)
    total_tokens = sum(sample["token_count"] for sample in klue_data)
    avg_tokens = total_tokens / total_samples if total_samples > 0 else 0
    
    # UNK 토큰 분석
    high_unk_samples = [sample for sample in klue_data if sample["unk_ratio"] > 10]
    
    print(f"총 샘플 수: {total_samples}")
    print(f"총 토큰 수: {total_tokens:,}")
    print(f"평균 토큰 수: {avg_tokens:.1f}")
    print(f"고UNK 샘플: {len(high_unk_samples)}개 ({len(high_unk_samples)/total_samples*100:.1f}%)")
    
    # 라벨링 난이도 평가
    if avg_tokens < 30:
        difficulty = "🟢 쉬움"
    elif avg_tokens < 50:
        difficulty = "🟡 보통"
    else:
        difficulty = "🔴 어려움"
    
    print(f"라벨링 난이도: {difficulty}")
    
    # 예상 라벨링 시간
    estimated_time_per_sample = avg_tokens * 3  # 토큰당 3초 가정
    total_estimated_time = estimated_time_per_sample * total_samples / 60  # 분 단위
    
    print(f"예상 라벨링 시간: {total_estimated_time:.1f}분 ({total_estimated_time/60:.1f}시간)")
    
    return {
        "total_samples": total_samples,
        "avg_tokens": avg_tokens,
        "estimated_time_minutes": total_estimated_time,
        "difficulty": difficulty,
        "high_unk_samples": len(high_unk_samples)
    }

def save_klue_data_batch(processed_files: List[Dict]) -> List[str]:
    """KLUE-BERT 처리 데이터 파일별 저장"""
    print(f"\n💾 KLUE-BERT 데이터 파일별 저장 중...")
    
    saved_files = []
    
    for file_info in processed_files:
        output_file = file_info["output_file"]
        samples = file_info["samples"]
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(samples, f, ensure_ascii=False, indent=2)
            
            file_size = len(json.dumps(samples, ensure_ascii=False)) / 1024
            
            print(f"✅ 저장 완료: {output_file}")
            print(f"   샘플 수: {len(samples)}개")
            print(f"   파일 크기: {file_size:.1f} KB")
            print(f"   평균 토큰: {file_info['avg_tokens']:.1f}개")
            print(f"   평균 UNK: {file_info['avg_unk_ratio']:.1f}%")
            print()
            
            saved_files.append(output_file)
            
        except Exception as e:
            print(f"❌ {output_file} 저장 실패: {e}")
            continue
    
    print(f"🎉 파일별 저장 완료!")
    print(f"   저장된 파일: {len(saved_files)}개")
    
    return saved_files

def create_batch_summary(processed_files: List[Dict], saved_files: List[str]):
    """배치 처리 요약 보고서 생성"""
    print(f"\n📊 배치 처리 요약 보고서")
    print("=" * 60)
    
    total_samples = sum(file_info["sample_count"] for file_info in processed_files)
    total_files = len(processed_files)
    
    if total_samples > 0:
        overall_avg_tokens = sum(file_info["avg_tokens"] * file_info["sample_count"] for file_info in processed_files) / total_samples
        overall_avg_unk = sum(file_info["avg_unk_ratio"] * file_info["sample_count"] for file_info in processed_files) / total_samples
    else:
        overall_avg_tokens = 0
        overall_avg_unk = 0
    
    print(f"📈 전체 통계:")
    print(f"   처리된 파일 수: {total_files}")
    print(f"   총 샘플 수: {total_samples:,}")
    print(f"   전체 평균 토큰 수: {overall_avg_tokens:.1f}")
    print(f"   전체 평균 UNK 비율: {overall_avg_unk:.1f}%")
    
    print(f"\n📁 파일별 상세:")
    print(f"{'원본 파일':<25} {'출력 파일':<25} {'샘플수':<8} {'평균토큰':<10} {'UNK%':<8}")
    print("-" * 80)
    
    for file_info in processed_files[:10]:  # 처음 10개만 표시
        source = file_info["source_file"][:24]
        output = file_info["output_file"][:24]
        samples = file_info["sample_count"]
        avg_tokens = file_info["avg_tokens"]
        avg_unk = file_info["avg_unk_ratio"]
        
        print(f"{source:<25} {output:<25} {samples:<8} {avg_tokens:<10.1f} {avg_unk:<8.1f}")
    
    if len(processed_files) > 10:
        print(f"... (총 {len(processed_files)}개 파일)")
    
    # 요약 파일 저장
    summary = {
        "processing_date": str(pd.Timestamp.now()),
        "total_files": total_files,
        "total_samples": total_samples,
        "overall_avg_tokens": overall_avg_tokens,
        "overall_avg_unk_ratio": overall_avg_unk,
        "file_details": processed_files,
        "saved_files": saved_files
    }
    
    with open("KLUE_batch_processing_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 요약 보고서 저장: KLUE_batch_processing_summary.json")

def create_labeling_template(klue_data: List[Dict], sample_count: int = 1):
    """라벨링 템플릿 생성 (다음 단계 준비)"""
    print(f"\n📋 라벨링 템플릿 생성 중... (샘플 {sample_count}개)")
    
    template = {
        "labeling_instructions": {
            "키워드 유형": [
                "인물: 가족, 남편, 딸, 아들, 어머니, 친구",
                "장소: 병원, 공원, 집, 여행지, 상점", 
                "시간: 봄, 여름, 작년, 어제, 아침",
                "활동: 산책, 요리, 여행, 운동, 만남",
                "감정: 행복, 슬픔, 기쁨, 그리움",
                "자연: 벚꽃, 바람, 달, 별"
            ],
            "라벨 규칙": {
                "B-KEY": "키워드 시작",
                "I-KEY": "키워드 내부 (2번째 토큰부터)",
                "O": "키워드 아님"
            }
        },
        "samples_to_label": []
    }
    
    for i in range(min(sample_count, len(klue_data))):
        sample = klue_data[i]
        
        labeling_sample = {
            "sample_id": sample["sample_id"],
            "original_answer": sample["original_answer"],
            "tokens": sample["tokens"],
            "labels": sample["labels"],  # 기본값 O로 설정됨
            "labeling_status": "pending",
            "keywords_to_find": []  # 라벨링 시 채우기
        }
        
        template["samples_to_label"].append(labeling_sample)
    
    # 템플릿 저장
    template_filename = "labeling_template.json"
    with open(template_filename, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 라벨링 템플릿 저장: {template_filename}")
    return template_filename

def main():
    """2단계 메인 실행 함수 - 32개 파일 배치 처리"""
    print("🎯 2단계: KLUE-BERT 데이터 재처리 (32개 파일 배치)")
    print("=" * 60)
    
    # 1. KLUE-BERT 설정
    tokenizer, model = setup_klue_bert()
    if not tokenizer:
        return
    
    # 2. 기존 데이터 로드 (32개 파일)
    all_original_answers, kobert_files_data = load_original_data()
    if not kobert_files_data:
        return
    
    # 3. KLUE-BERT로 배치 재처리
    processed_files = reprocess_with_klue_bert_batch(tokenizer, kobert_files_data)
    
    # 4. 파일별 저장
    saved_files = save_klue_data_batch(processed_files)
    
    # 5. 배치 처리 요약
    create_batch_summary(processed_files, saved_files)
    
    # 6. 완료 보고서
    print(f"\n🎉 32개 파일 배치 처리 완료!")
    print("=" * 50)
    
    if processed_files:
        total_samples = sum(f["sample_count"] for f in processed_files)
        avg_tokens = sum(f["avg_tokens"] * f["sample_count"] for f in processed_files) / total_samples if total_samples > 0 else 0
        avg_unk = sum(f["avg_unk_ratio"] * f["sample_count"] for f in processed_files) / total_samples if total_samples > 0 else 0
        
        print(f"✅ 처리된 파일: {len(processed_files)}개")
        print(f"✅ 총 샘플: {total_samples:,}개")
        print(f"✅ 평균 토큰 수: {avg_tokens:.1f}개")
        print(f"✅ 평균 UNK 비율: {avg_unk:.1f}%")
        print(f"✅ 저장된 파일: {len(saved_files)}개")
    
    print(f"\n📁 생성된 파일들:")
    for saved_file in saved_files[:5]:  # 처음 5개만 표시
        print(f"   - {saved_file}")
    if len(saved_files) > 5:
        print(f"   - ... (총 {len(saved_files)}개)")
    
    print(f"\n📋 다음 단계 (3단계):")
    print(f"1. KLUE_tokenized_answers*.json 파일들 확인")
    print(f"2. 키워드 라벨링 작업 준비")
    print(f"3. 토큰 품질 검증")
    
    # 첫 번째 파일 샘플 보기
    if processed_files and processed_files[0]["samples"]:
        sample = processed_files[0]["samples"][0]
        print(f"\n💡 처리 결과 예시 ({processed_files[0]['output_file']}):")
        print(f"원본: {sample['original_answer'][:50]}...")
        print(f"토큰: {sample['tokens'][:8]}...")
        print(f"토큰 수: {sample['token_count']} (UNK: {sample['unk_count']})")
    
    print(f"\n🎯 성공! 이제 KLUE-BERT 토크나이즈 데이터가 준비되었습니다!")
    
    return processed_files, saved_files

if __name__ == "__main__":
    main()