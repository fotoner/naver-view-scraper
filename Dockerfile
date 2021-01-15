FROM python:3.8.5
MAINTAINER Fotone <jaemuon5582@gmail.com>

RUN mkdir -p /app
WORKDIR /app

ADD ./ ./

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "-u", "./main.py"]
# TODO 도커파일에 셀레니움 관련 설치 코드 추가하기