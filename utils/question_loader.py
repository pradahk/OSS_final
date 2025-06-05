import pandas as pd
import os
from typing import List, Optional

def load_questions_from_csv(csv_path: str = "questions.csv") -> List[str]:
    """CSV 파일에서 질문들을 읽어와서 리스트로 반환"""
    try:
        # 현재 파일의 디렉토리를 기준으로 절대 경로 생성
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        csv_full_path = os.path.join(parent_dir, csv_path)
        
        if not os.path.exists(csv_full_path):
            print(f"CSV 파일을 찾을 수 없습니다: {csv_full_path}")
            return []
        
        # 여러 인코딩으로 시도
        encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_full_path, encoding=encoding)
                print(f"CSV 파일 로딩 성공 (인코딩: {encoding})")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            print("모든 인코딩으로 시도했지만 CSV 파일을 읽을 수 없습니다.")
            return []
        
        # 질문 컬럼 찾기
        question_column = find_question_column(df)
        if question_column is None:
            return []
        
        # 질문 리스트 생성
        questions = []
        for idx, question_text in enumerate(df[question_column].dropna()):
            question_text = str(question_text).strip()
            if question_text and question_text.lower() not in ['nan', 'null', '']:
                questions.append(question_text)
        
        print(f"총 {len(questions)}개의 질문을 로드했습니다.")
        return questions
        
    except Exception as e:
        print(f"CSV 로딩 중 오류 발생: {e}")
        return []

def find_question_column(df: pd.DataFrame) -> Optional[str]:
    """데이터프레임에서 질문 컬럼 찾기"""
    possible_columns = [
        'question', 'question_text', '질문', 'questions',
        'Question', 'QUESTION', 'Question_Text', 'QUESTION_TEXT',
        '문제', '문항', 'item', 'Item'
    ]
    
    for col in possible_columns:
        if col in df.columns:
            print(f"질문 컬럼 발견: {col}")
            return col
    
    # 첫 번째 컬럼을 질문 컬럼으로 사용
    if len(df.columns) > 0:
        question_column = df.columns[0]
        print(f"첫 번째 컬럼을 질문 컬럼으로 사용: {question_column}")
        return question_column
    
    return None