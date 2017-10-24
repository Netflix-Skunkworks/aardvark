
ARG AARDVARK_IMAGES_TAG=latest
FROM aardvark-base:${AARDVARK_IMAGES_TAG}

LABEL author="scottbrown0001@gmail.com"

ARG AARDVARK_DATA_DIR="/usr/share/aardvark-data"

ENV AARDVARK_ACCOUNTS=''

RUN mkdir -p $AARDVARK_DATA_DIR
WORKDIR $AARDVARK_DATA_DIR

CMD aardvark update -a $AARDVARK_ACCOUNTS
