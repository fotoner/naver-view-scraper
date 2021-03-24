FROM python:3.8.5
MAINTAINER Fotone <jaemuon5582@gmail.com>

RUN mkdir -p /app
WORKDIR /app

ADD ./ ./

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "-u", "./main.py"]
# TODO 도커파일에 셀레니움 관련 설치 코드 추가하기

# wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
# sudo apt-get update
# sudo apt-get install google-chrome-stable
# sudo rm -rf /etc/apt/sources.list.d/google.list