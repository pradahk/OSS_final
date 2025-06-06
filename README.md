# OSS_final
smwu 24 OSS final team project

branch : gptapiTokenizing

날짜 : 5/30

수행내용 : gpt api로 예시 답변 csv 데이터를 형태소 분리하여 라벨링 가능한 형태로 변경하여 csv 파일로 저장(gpt-3.5-turbo 모델 사용).

방법 : " {cleaned_text}'를 형태소 단위로 분리해줘. 각 형태소는 공백으로 구분하고, 품사 정보는 생략해줘. " 라는 문장을 gpt에 넣어 수행. Token_gptapi 폴더 안에 " {base_name}_custom_token.csv " 이름으로 라벨링 수행이 가능한 부분을 포함한 형태소 토큰화 예시 답변 데이터를 생성함.
