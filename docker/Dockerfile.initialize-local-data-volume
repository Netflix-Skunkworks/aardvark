
ARG AARDVARK_IMAGES_TAG=latest
FROM aardvark-base:${AARDVARK_IMAGES_TAG}

LABEL author="scottbrown0001@gmail.com"

ARG AARDVARK_DATA_DIR

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

RUN mkdir -p $AARDVARK_DATA_DIR
WORKDIR $AARDVARK_DATA_DIR

# We need to run this once with a volume attached when the container
# is launched.
CMD aardvark create_db
