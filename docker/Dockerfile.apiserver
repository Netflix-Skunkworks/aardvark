
ARG AARDVARK_IMAGES_TAG=latest
FROM aardvark-base:${AARDVARK_IMAGES_TAG}

LABEL author="scottbrown0001@gmail.com"

ARG AARDVARK_DATA_DIR="/usr/share/aardvark-data"
ENV AARDVARK_API_PORT="5000"

RUN mkdir -p $AARDVARK_DATA_DIR

# This is superflous unless we're using a local data volume.
WORKDIR $AARDVARK_DATA_DIR

CMD aardvark start_api -b 0.0.0.0:$AARDVARK_API_PORT
