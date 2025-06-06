import os
import pandas as pd
from openai import OpenAI
import time
import re
import csv

client = OpenAI(
    api_key="my api key"
)

def analyze_morphemes_with_chatgpt(text, model="gpt-3.5-turbo", max_retries=3, delay_sec=1):
    cleaned_text = re.sub(r'[^\w\s\.\,\!\?\(\)\<\>\-\=\+\/\[\]\{\}\:]', '', text)
    if not cleaned_text.strip():
        return []

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that performs Korean morphological analysis. Output the morphemes separated by a space. Do not include part-of-speech tags or any other explanations. Just the space-separated morphemes."},
                    {"role": "user", "content": f"'{cleaned_text}'를 형태소 단위로 분리해줘. 각 형태소는 공백으로 구분하고, 품사 정보는 생략해줘."}
                ],
                max_tokens=200,
                temperature=0.1,
                timeout=15
            )
            morpheme_string = response.choices[0].message.content.strip()
            if morpheme_string.startswith("형태소: "):
                morpheme_string = morpheme_string[len("형태소: "):].strip()
            
            morpheme_string = morpheme_string.replace("'", "").replace('"', '')

            if not morpheme_string or morpheme_string.lower() == "none":
                return []
            
            return morpheme_string.split(' ')
        except Exception as e:
            print(f"API 호출 중 오류 발생 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay_sec * (attempt + 1))
            else:
                return None
    return None

def process_single_csv_file_and_save_morphemes_custom(filepath, output_filename):
    processed_rows = []
    filename = os.path.basename(filepath)

    if not os.path.exists(filepath):
        print(f"오류: 지정된 파일 '{filepath}'를 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    print(f"\n--- 파일 '{filename}' 처리 중 ---")
    try:
        df = pd.read_csv(filepath, header=None)
        sentences = df.iloc[:, 0].tolist() 
        
        for i, sentence in enumerate(sentences):
            if pd.isna(sentence) or not str(sentence).strip():
                print(f"  - 문장 {i+1} (파일 {filename}): 빈 문자열 또는 NaT 값. 건너뜁니다.")
                continue

            sentence_str = str(sentence).strip()

            print(f"  - 문장 {i+1} 형태소 분석 중: {sentence_str[:50]}...")
            
            morphemes_list = analyze_morphemes_with_chatgpt(sentence_str)
            
            current_row = []
            if morphemes_list is not None:
                for morpheme in morphemes_list:
                    current_row.append(morpheme)
                    current_row.append("")
            else:
                current_row.append(f"API_ERROR: {sentence_str[:50]}...")
            processed_rows.append(current_row)
            time.sleep(0.05)

    except Exception as e:
        print(f"오류: 파일 '{filename}' 처리 중 예상치 못한 오류 발생: {e}")
        return

    with open(output_filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        for row_data in processed_rows:
            writer.writerow(row_data)
    print(f"\n형태소 분석 결과가 '{output_filename}'에 저장되었습니다. 이제 이 파일을 열어 수동 라벨링을 수행하세요.")

if __name__ == "__main__":
    target_csv_file_name = "example32.csv"
    base_name = os.path.splitext(target_csv_file_name)[0]
    output_csv_file_name = f"{base_name}_custom_token.csv"
    target_csv_file_path = target_csv_file_name
    process_single_csv_file_and_save_morphemes_custom(target_csv_file_path, output_csv_file_name)