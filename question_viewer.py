import os
import pandas as pd

# CSV 파일 존재 여부
print(f"CSV 파일 존재: {os.path.exists('questions.csv')}")

# CSV 내용 미리보기
if os.path.exists('questions.csv'):
    df = pd.read_csv('questions.csv')
    print(f"CSV 행 수: {len(df)}")
    print("CSV 컬럼들:", df.columns.tolist())