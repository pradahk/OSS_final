KoBERT를 학습시킬 수 있는 데이터를 만들기 위한 작업

1단계 : 예시 답변을 csv폴더로 변환하여 example1부터 32까지 저장

2단계 : KoBERT가 이해할 수 있도록 예시 답변 토큰화 - AutoTokenizer.from_pretrained('skt/kobert-base-v1')를 사용하여 자체 토크나이징 진행

3단계 : 사람이 이해할 수 있도록 예시 답변 토큰화 - 수동 라벨링 작업을 위해서는 사람이 이해할 수 있는 형식의 형태소 토크나이징 필요. 따라서 konlpy를 사용하여 형태소 토큰화 후 수동 라벨링 진행

4단계 : 형태소 라벨링 토큰의 결과를 KoBERT 토큰과 결합하여 학습 데이터 완성 - 토큰 시퀀스(수동 라벨링에 사용된 형태소 토큰, KoBERT의 서브워드 토큰) 간의 매핑(alignment) 진행

------

그러나 Windows 환경에서는 3단계 진행이 어려움.

오류: Mecab 형태소 분석기 로드 중 오류 발생: Install MeCab in order to use it: http://konlpy.org/en/latest/install/

Konlpy 및 JPype1이 설치되었는지, 환경 변수 (PATH, JAVA_HOME) 설정이 올바른지 확인해주세요.

Mecab 본체 ('C:\mecab') 및 사전 ('C:\mecab\mecab-ko-dic')이 올바르게 배치되었는지도 확인해주세요

라는 오류가 계속 발생했고

1. C:\mecab에 Mecab 본체와 사전이 올바르게 위치합니다.

2. JAVA_HOME 환경 변수가 정확하게 설정되었고, echo %JAVA_HOME%도 정상적으로 출력됩니다.

3. Path 환경 변수 순서도 C:\mecab\bin과 %JAVA_HOME%\bin이 적절한 위치에 있습니다.

4. java.exe와 mecab.exe 파일 존재도 확인했습니다.

5. JPype1과 konlpy 패키지는 oss-final 가상 환경에 올바르게 설치되어 있습니다.

6. Visual C++ Redistributable도 설치/복구했습니다.

7. 파이썬 스크립트도 konlpy.tag.Mecab을 사용하도록 수정했습니다.

와 같은 방법을 시도했으니 문제는 해결되지 않고 결국 실행 환경을 윈도우에서 Macos로 변경하라는 결론이 나옴.
