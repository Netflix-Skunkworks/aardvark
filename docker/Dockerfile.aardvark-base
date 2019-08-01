
FROM python:2

LABEL author="scottbrown0001@gmail.com"

COPY aardvark /tmp/aardvark
WORKDIR /tmp/aardvark

# Update the repository and install aardvark.
RUN apt-get update && \
    pip install .

# Create aardvark configuration.
ARG AARDVARK_CONFIG_DIR="/etc/aardvark"
ARG AARDVARK_ROLE=""
ARG SWAG_BUCKET=""
ARG AARDVARK_DB_URI=""
ARG AARDVARK_DATA_DIR

RUN mkdir -p $AARDVARK_CONFIG_DIR
WORKDIR $AARDVARK_CONFIG_DIR

RUN if [ -z "$AARDVARK_DB_URI" -a -n "$AARDVARK_DATA_DIR" ] ; then \
		AARDVARK_DB_URI="sqlite:///$AARDVARK_DATA_DIR/aardvark.db"; \
		fi; \
	AARDVARK_CONFIG_OPTIONS=$( \
		printf "%s%s%s" \
			"$(if [ -n "$AARDVARK_ROLE" ] ; then echo "-a $AARDVARK_ROLE "; fi)" \
			"$(if [ -n "$SWAG_BUCKET" ] ; then echo "-b $SWAG_BUCKET "; fi)" \
			"$(if [ -n "$AARDVARK_DB_URI" ] ; then echo "-d $AARDVARK_DB_URI "; fi)" \
		); \
	aardvark config --no-prompt $AARDVARK_CONFIG_OPTIONS

RUN rm -r /tmp/aardvark