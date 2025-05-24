import pandas as pd
from transformers import AutoTokenizer
import os
import json # JSON 저장을 위해 임포트

print("--- 스크립트 시작: 답변 토크나이징 ---")

# 1단계: CSV 파일 로드
csv_file_path = 'example32.csv' # 사용하실 CSV 파일 이름
try:
    df = pd.read_csv(csv_file_path, header=None)
    answers = df.iloc[:, 0].dropna().tolist()

    if not answers:
        print(f"오류: '{csv_file_path}' 파일에 읽을 수 있는 답변이 없습니다. 파일 내용을 확인해주세요.")
        exit()

    print(f"로드된 답변 개수: {len(answers)}")
    print("첫 5개 답변:", answers[:5])

except FileNotFoundError:
    print(f"오류: '{csv_file_path}' 파일을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
    exit()
except Exception as e:
    print(f"CSV 파일 로드 중 오류 발생: {e}")
    # 인코딩 문제일 수 있으므로, UTF-8과 CP949를 시도해 볼 수 있음을 안내
    print("CSV 파일의 인코딩 문제일 수 있습니다. pd.read_csv에 encoding='utf-8' 또는 'cp949' 등을 시도해보세요.")
    exit()


# 2단계: KoBERT 토크나이저 로드
# spiece.model 파일이 파이썬 스크립트와 같은 폴더에 있다고 가정합니다.
script_dir = os.path.dirname(os.path.abspath(__file__))
kobert_spiece_model_path = os.path.join(script_dir, 'spiece.model')

# spiece.model 파일 존재 여부 확인
if not os.path.exists(kobert_spiece_model_path):
    print(f"오류: spiece.model 파일이 다음 경로에 없습니다: {kobert_spiece_model_path}")
    print("spiece.model 파일을 파이썬 스크립트와 같은 폴더에 두었는지 확인해주세요.")
    exit()
else:
    print(f"spiece.model 파일 경로 확인: {kobert_spiece_model_path}")


try:
    print("KoBERT 토크나이저 로드 시도 중...")
    tokenizer = AutoTokenizer.from_pretrained(
        'skt/kobert-base-v1',
        vocab_file=kobert_spiece_model_path,
        # local_files_only=True # 인터넷 연결 없이 로컬 파일만 사용하려면 주석 해제 (필요시)
    )
    print("KoBERT 토크나이저 로드 완료.")
except Exception as e:
    print(f"!!!! KoBERT 토크나이저 로드 중 치명적인 오류 발생: {e}")
    print(f"'{kobert_spiece_model_path}' 파일을 확인하거나 transformers 라이브러리 설치를 확인해주세요.")
    exit()


# 3단계: 답변 토크나이징 및 결과 저장 준비
tokenized_outputs = []
for i, answer in enumerate(answers):
    # 토크나이징 수행
    encoded_input = tokenizer(
        answer,
        return_tensors='pt', # PyTorch 텐서 형태로 반환
        truncation=True,    # 최대 길이를 초과하는 경우 자르기 (max_length 미지정 시 모델 기본값 따름)
        padding=True        # 배치 내 가장 긴 시퀀스 길이에 맞춰 패딩
    )
    
    # 토크나이징 결과를 리스트에 추가
    tokenized_outputs.append({
        'original_answer': answer,
        'input_ids': encoded_input['input_ids'][0].tolist(), # PyTorch 텐서를 리스트로 변환
        'attention_mask': encoded_input['attention_mask'][0].tolist(),
        'token_type_ids': encoded_input.get('token_type_ids', [0]*len(encoded_input['input_ids'][0])).tolist(), # 없을 경우 기본값
        'tokens': tokenizer.convert_ids_to_tokens(encoded_input['input_ids'][0].tolist()) # 실제 토큰 문자열
    })
    
    # 진행 상황 출력 (선택 사항)
    if (i + 1) % 100 == 0:
        print(f"진행 상황: {i + 1}/{len(answers)} 답변 토크나이징 완료.")


# 4단계: 토크나이징된 결과 JSON 파일로 저장
output_json_path = 'tokenized_answers32.json' # 저장될 JSON 파일 이름
try:
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(tokenized_outputs, f, ensure_ascii=False, indent=4) # 한글 깨짐 방지 및 보기 좋게 들여쓰기
    print(f"\n성공: 모든 답변이 토크나이징되어 '{output_json_path}' 파일에 저장되었습니다.")
except Exception as e:
    print(f"오류: 토크나이징 결과 저장 중 오류 발생: {e}")

print("\n--- 스크립트 완료 ---")