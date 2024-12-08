FROM python:3.12

RUN mkdir /voicely-ping

WORKDIR /voicely-ping

COPY ["voicely-ping.py", "README.md", "./legal", "requirements.txt", "./"]

RUN pip install -r requirements.txt

CMD ["python", "voicely-ping.py"]