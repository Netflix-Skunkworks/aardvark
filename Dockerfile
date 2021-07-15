FROM python:3.8

RUN apt-get update -y \
    && apt-get upgrade -y \
    && mkdir -p /usr/src/aardvark \
    && pip install --upgrade wheel setuptools pip

WORKDIR /usr/src/aardvark

COPY . /usr/src/aardvark
RUN pip install .

WORKDIR /etc/aardvark

ENV AARDVARK_DATA_DIR=/data \
    AARDVARK_ROLE=Aardvark \
    ARN_PARTITION=aws \
    AWS_DEFAULT_REGION=us-east-1 \
    FLASK_APP=aardvark

EXPOSE 5000

COPY ./config.yaml .
COPY ./entrypoint.sh /etc/aardvark/entrypoint.sh

ENTRYPOINT [ "/etc/aardvark/entrypoint.sh" ]

CMD [ "aardvark" ]
