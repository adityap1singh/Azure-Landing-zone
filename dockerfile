FROM ubuntu:24.04

LABEL maintainer="Aditya Singh"

RUN apt-get update && \
    apt-get install -y curl wget git unzip && \
    apt-get clean

WORKDIR /app

CMD ["bash"]