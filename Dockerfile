FROM python:3.12.3-slim
RUN apt-get update && apt-get install build-essential -y

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 1844
RUN chmod a+x run.sh
