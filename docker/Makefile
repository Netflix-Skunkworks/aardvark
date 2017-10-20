


help:		## Display this message.
	@printf '$(subst $(newline),\n,${HELPPROLOGUE})'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		egrep "\b(aardvark-all|aardvark-sqlite)\b" | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m    %-24s\033[0m %s\n", $$1, $$2}'
	@printf '$(subst $(newline),\n,${HELPINTERLUDE1})'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep "clean" | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m    %-24s\033[0m %s\n", $$1, $$2}'
	@printf '$(subst $(newline),\n,${HELPINTERLUDE2})'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		egrep -v "\b(aardvark-all|aardvark-sqlite|clean.*|help)\b" | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m    %-24s\033[0m %s\n", $$1, $$2}'
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep help | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m    %-24s\033[0m %s\n", $$1, $$2}'
	@printf '$(subst $(newline),\n,${HELPEPILOGUE})'

define HELPPROLOGUE

To build an aardvark deployment from scratch, make one of these targets:


endef

define HELPINTERLUDE1

    The aardvark-sqlite build includes all the products from the aardvark-all
    build, and additionally creates and initializes a shared data volume for
    the sqlite database.

    See below for examples and for environment variable settings required to
    properly configure your aardvark containers build and deployment.


Remove intermediate and final files and/or docker images with the following
cleanup targets:


endef

define HELPINTERLUDE2


Additional available targets include:


endef

define HELPEPILOGUE


Note:

    * New docker images will overwrite existing images created by this Makefile.
      Set the AARDVARK_IMAGES_TAG environment variable to specify a tag to
      distinguish new images created with this Makefile from existing images.

    * Nothing you can do with this Makefile will stop or remove any existing
      container.

    * Nothing you can do with this Makefile will remove or overwrite an
      existing aardvark-data volume. If the AARDVARK_IMAGES_TAG environment
      variable is set when you make the aardvark-sqlite or the
      aardvark-data-volume target, a new aardvark-data-$$AARDVARK_IMAGES_TAG
      volume will be created if it does not already exist.



Environment Variables
=====================

A number of build time and run-time configuration options are controlled with
environment variables.


Configuration build time environment variables are passed to aardvark-config
when the base images for the aardvark collector and aardvark apiserver
containers are built.

                        aardvark
Configuration           config
Build Time Variable     Parameter       Notes
-------------------     ---------       ---------------------------------------
AARDVARK_DB_URI         db-uri          Required when not using a local mysql
                                        database.

AARDVARK_ROLE           aardvark-role   Required if the sts:AssumeRole for
                                        aardvark is not named "Aardvark".

SWAG_BUCKET             swag-bucket     Required when using SWAG.

Note that if set the values of these environment variables are automatically
picked up by the make process without any explicit passing of parameters.


Runtime environment variables need to be set when launching the collector or
apiserver containers.

Runtime Variable        Used by         Notes
-------------------     ---------       ---------------------------------------
AARDVARK_ACCOUNTS       collector       Optional if using SWAG, otherwise
                                        required. Set this to a list of SWAG
                                        account name tags or a list of AWS
                                        account numbers from which to collect
                                        Access Advisor records.

AWS_ACCESS_KEY_ID       collector       Required if not running on an EC2
AWS_SECRET_ACCESS_KEY   collector       instance with an appropriate Instance
                                        Profile. Set these to the credentials of
                                        an AWS IAM user with permission to
                                        sts:AssumeRole to the Aardvark audit
                                        role.

AARDVARK_API_PORT       apiserver       Optional. Specifies the container port 
                                        on which the aardvark API server
                                        listens. The default is 5000, and this
                                        environment variable is unneeded if the
                                        apiserver container is run with
                                        "-p 127.0.0.1:[HOST_PORT]:5000".
                                        If for some reason you do set this
                                        variable, run the aardvark apiserver
                                        with the $$AARDVARK_API_PORT published
                                        to the host.

Note that these values must be explicitly specified on the "docker run" command
line when launching containers.


Customization build time variables control other aspects of the build process.

Customization
Build Time Variable     Notes
-------------------     ------------------------------------------------------
AARDVARK_IMAGES_TAG     A common tag to apply to the docker images and volumes
                        created by the build process.

                          * If changed, be sure to run "make clean" prior to
                            the next build.

                          * If you want to remove existing images tagged with
                            the old value, run "make clean-docker" before
                            changing the value.


Examples
========


A typical production deployment
-----------------------------------------------------------

    Here we see the settings and build steps to create and run a typical
    production deployment, using SWAG and an RDS database, on an EC2 instance
    with an instance profile granting the required sts::AssumeRole permissions.

    $$ export AARDVARK_ROLE="<MyAardvarkRoleName>"
    $$ export AARDVARK_DB_URI="<database URI>"
    $$ export SWAG_BUCKET="<swag-bucket-name>"
    $$ make clean-all
    $$ make aardvark-all
    $$ docker run -v aardvark-data:/usr/share/aardvark-data --rm aardvark-collector
    $$ docker run -v aardvark-data:/usr/share/aardvark-data \\
      -p 127.0.0.1:80:5000 aardvark-apiserver

    * The SWAG_BUCKET build time environment variable is set so that aardvark
      will be configured to use SWAG.

    * The AARDVARK_DB_URI build time environment variable is set to point to
      the appropriate external database.

    * With SWAG the AARDVARK_ACCOUNTS runtime environment variable is optional.
      Set it to a list of SWAG account name tags to collect from or leave it
      undefined to collect from all accounts known to SWAG.


A typical standalone or test deployment
-----------------------------------------------------------

    Here we see the settings and build steps to create and run a typical
    deployment in a standalone environment such as might be used for local
    testing.

    $$ export AARDVARK_ROLE="<MyAardvarkRoleName>"
    $$ make clean-all
    $$ make aardvark-sqlite
    $$ export AWS_ACCESS_KEY_ID=<aws_access_key_id>
    $$ export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key>
    $$ export AARDVARK_ACCOUNTS="<account_number>[ account_number [...]]"
    $$ docker run -v aardvark-data:/usr/share/aardvark-data \\
      -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY \\
      -e AARDVARK_ACCOUNTS --rm aardvark-collector
    $$ docker run -v aardvark-data:/usr/share/aardvark-data \\
      -p 127.0.0.1:80:5000 aardvark-apiserver

    * The AARDVARK_ACCOUNTS runtime environment variable is used to pass one or
      more AWS account numbers directly to the aardvark-collector container.

    * In contrast to running on an EC2 instance configured with an Instance
      Profile that provides the collector with necessary sts::AssumeRole
      permissions, the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY runtime
      environment variables are set to specify an AWS IAM user with the
      necessary permissions.

    * At runtime the aardvark-data shared volume providing a local sqlite
      database is mounted on both the collector and the apiserver. The mount
      point "/usr/share/aardvark-data" is created when the docker images are
      built.

    * The underlying boto3 library will automatically use the credentials it
      finds in the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY runtime
      environment variables.

      Be aware that setting these in the container runtime environment makes
      them visible to anyone who can attach a shell to the running container,
      but does not make them visible in the underlying image or its history.

      Of course, do not save the AWS IAM credentials anywhere other than your
      .aws/credentials file.


endef

# This lets us get the HELPTEXT string across the make/shell expansion
# combination.
define newline


endef


# - - - - - - - - - - - - - - - -
# Update these to rev the phantomjs version.
# - - - - - - - - - - - - - - - -
PHANTOMJS_VERSION = phantomjs-2.1.1-linux-x86_64
PHANTOMJS_SHA = 86dd9a4bf4aee45f1a84c9f61cf1947c1d6dce9b9e8d2a907105da7852460d2f
# PHANTOMJS_2_1_1_SHA = 86dd9a4bf4aee45f1a84c9f61cf1947c1d6dce9b9e8d2a907105da7852460d2f

PHANTOMJS_ARCHIVE = $(PHANTOMJS_VERSION).tar.bz2

# - - - - - - - - - - - - - - - -
# Many build steps are docker build or docker run, which create no
# actual target and would always rebuild. These files are created by
# the corresponding build steps to indicate that the step is complete.
# They are among those removed by "make clean".
# - - - - - - - - - - - - - - - -
ARTIFACTS_DIR = artifacts
AARDVARK_BASE_DOCKER_BUILD_PSEUDO = $(ARTIFACTS_DIR)/aardvark-base-docker-build-$(AARDVARK_IMAGES_TAG)
AARDVARK_DATA_DOCKER_BUILD_PSEUDO = $(ARTIFACTS_DIR)/aardvark-data-docker-build-$(AARDVARK_IMAGES_TAG)
AARDVARK_DATA_DOCKER_RUN_PSEUDO = $(ARTIFACTS_DIR)/aardvark-data-docker-run-$(AARDVARK_IMAGES_TAG)
AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO = $(ARTIFACTS_DIR)/aardvark-apiserver-docker-build-$(AARDVARK_IMAGES_TAG)
AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO = $(ARTIFACTS_DIR)/aardvark-collector-docker-build-$(AARDVARK_IMAGES_TAG)

# - - - - - - - - - - - - - - - -
# These are removed by "make clean".
# - - - - - - - - - - - - - - - -
ALL_CLEANUP = \
	$(AARDVARK_BASE_DOCKER_BUILD_PSEUDO) \
	$(AARDVARK_DATA_DOCKER_BUILD_PSEUDO) \
	$(AARDVARK_DATA_DOCKER_RUN_PSEUDO) \
	$(AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO) \
	$(AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO) \
	$(PHANTOMJS_ARCHIVE) \
	$(PHANTOMJS_ARCHIVE).shasum \
	aardvark \
	phantomjs*

# - - - - - - - - - - - - - - - -
# These are removed by "make clean-docker".
# - - - - - - - - - - - - - - - -
ALL_DOCKER_CLEANUP = \
	aardvark-apiserver \
	aardvark-collector \
	aardvark-data-init \
	aardvark-base

# - - - - - - - - - - - - - - - -
# These are target lists in multiple places.
# - - - - - - - - - - - - - - - -
PREREQUISITES = aardvark phantomjs
AARDVARK_SERVICE = aardvark-collector aardvark-apiserver

# - - - - - - - - - - - - - - - -
# This is passed to the aardvark-base docker build to create the mount
# point for the shared volume if an sqlite local database is used; the
# same value is passed to the aardvark-data-volume build and run to
# initialize the shared data volume. It *also* needs to be consistent
# with the mount location specified when the apiserver and collector
# containers are launched, but that happens outside the scope of this
# Makefile. The example in the help text shows the correct location to
# use.
# - - - - - - - - - - - - - - - -
AARDVARK_DATA_DIR = /usr/share/aardvark-data

# - - - - - - - - - - - - - - - -
# The default when invoking aardvark config with no db_uri parameter
# is to set the DB_URI to the sqlite path to /usr/share/aardvark-data.
# Setting AARDVARK_DATA_DIR at the aardvark-sqlite level is therefore
# superfluous, but the value needs to be in sync with the shared data
# volume mount point so we make it explicit here.
# - - - - - - - - - - - - - - - -
aardvark-sqlite $(AARDVARK_DATA_DOCKER_RUN_PSEUDO): AARDVARK_DATA_DIR = /usr/share/aardvark-data

# - - - - - - - - - - - - - - - -
# These are provided for entry points (the <X> in "make <X>"). They
# have no (real or stand-in) targets and should not be used as
# dependencies as this will always trigger upstream rebuilds.
# - - - - - - - - - - - - - - - -
aardvark-all: $(AARDVARK_SERVICE)		## Build the collector and apiserver docker images.
aardvark-sqlite: $(AARDVARK_DATA_DOCKER_RUN_PSEUDO) $(AARDVARK_SERVICE) ## Build aardvark-all and a shared volume sqlite database.
aardvark-apiserver: $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO) $(AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO)		## Build the aardvark apiserver docker image.
aardvark-collector: $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO) $(AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO)		## Build the aardvark collector docker image.
aardvark-data-volume: $(AARDVARK_DATA_DOCKER_RUN_PSEUDO)		## Create and initialize the sqlite database shared volume.
aardvark-base: $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO)	## Create the base docker image for subsequent aardvark images.
prerequisites: $(PREREQUISITES)		## Fetch the phantomjs package and aardvark repository if not present.

# - - - - - - - - - - - - - - - -
.PHONY: clean clean-docker clean-all help

clean:		## Remove intermediate, target and pseudo-target files and directories.
	-rm -rf $(ALL_CLEANUP)

clean-docker:		## Remove existing docker images (prompts for confirmation).
	@echo "This will remove the following docker images if they exist:"; \
	for image in $(ALL_DOCKER_CLEANUP) ; do \
		echo "    $$image$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)"; \
		done; \
    read -p "Proceed? (y/n) " response; \
    case $$response in \
        [Yy]* ) break;; \
        * ) echo "skipping docker cleanup"; exit;; \
	    esac; \
	for image in $(ALL_DOCKER_CLEANUP) ; do \
		if [ -n "$$(docker image ls "$$image$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)" | grep -v REPOSITORY)" ]; then \
			echo "removing $$image with \"docker image rm $$image\""; \
			docker image rm "$$image$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)"; \
			fi; \
		done

clean-all: clean clean-docker		## Equivalent to 'make clean' and 'make clean-docker'.

# - - - - - - - - - - - - - - - -
$(AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO):
	docker build \
		-t "aardvark-collector$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)" \
		-f Dockerfile.collector \
		--build-arg AARDVARK_IMAGES_TAG=$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "$$AARDVARK_IMAGES_TAG"; else echo "latest"; fi) \
		.; \
	AARDVARK_COLLECTOR_IMAGE_LS=$$(docker image ls | egrep "aardvark-collector *$$AARDVARK_IMAGES_TAG"); \
	mkdir -p $(ARTIFACTS_DIR); \
	rm -f $(AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO); \
	if [ -n "$$AARDVARK_COLLECTOR_IMAGE_LS" ] ; then \
		echo "$$AARDVARK_COLLECTOR_IMAGE_LS" > $(AARDVARK_COLLECTOR_DOCKER_BUILD_PSEUDO); \
		fi

# - - - - - - - - - - - - - - - -
$(AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO):
	docker build \
		-t "aardvark-apiserver$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)" \
		-f Dockerfile.apiserver \
		--build-arg AARDVARK_IMAGES_TAG=$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "$$AARDVARK_IMAGES_TAG"; else echo "latest"; fi) \
		.; \
	AARDVARK_APISERVER_IMAGE_LS=$$(docker image ls | egrep "aardvark-apiserver *$$AARDVARK_IMAGES_TAG"); \
	mkdir -p $(ARTIFACTS_DIR); \
	rm -f $(AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO); \
	if [ -n "$$AARDVARK_APISERVER_IMAGE_LS" ] ; then \
		echo "$$AARDVARK_APISERVER_IMAGE_LS" > $(AARDVARK_APISERVER_DOCKER_BUILD_PSEUDO); \
		fi

# - - - - - - - - - - - - - - - -
$(AARDVARK_DATA_DOCKER_RUN_PSEUDO): $(AARDVARK_DATA_DOCKER_BUILD_PSEUDO)
	mkdir -p $(ARTIFACTS_DIR); \
	if [ -n "$$(docker volume ls | egrep "\baardvark-data$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "-$$AARDVARK_IMAGES_TAG"; fi)$$")" ] ; then \
		echo "Using existing aardvark-data docker volume"; \
		echo "Using existing aardvark-data docker volume" > $(AARDVARK_DATA_DOCKER_RUN_PSEUDO); \
	else \
		docker volume create aardvark-data$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "-$$AARDVARK_IMAGES_TAG"; fi); \
		rm -f $(AARDVARK_DATA_DOCKER_RUN_PSEUDO); \
		docker run -v aardvark-data$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "-$$AARDVARK_IMAGES_TAG"; fi):$(AARDVARK_DATA_DIR) --rm aardvark-data-init$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi); \
		echo "initialized data directory $(AARDVARK_DATA_DIR)" > $(AARDVARK_DATA_DOCKER_RUN_PSEUDO); \
		fi

$(AARDVARK_DATA_DOCKER_BUILD_PSEUDO): $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO)
	docker build \
		-t "aardvark-data-init$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)" \
		-f Dockerfile.initialize-local-data-volume  \
		--build-arg AARDVARK_IMAGES_TAG=$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo "$$AARDVARK_IMAGES_TAG"; else echo "latest"; fi) \
		--build-arg AARDVARK_DATA_DIR=$(AARDVARK_DATA_DIR) \
		.; \
	AARDVARK_DATA_INIT_IMAGE_LS=$$(docker image ls | egrep "aardvark-data-init *$$AARDVARK_IMAGES_TAG"); \
	mkdir -p $(ARTIFACTS_DIR); \
	rm -f $(AARDVARK_DATA_DOCKER_BUILD_PSEUDO); \
	if [ -n "$$AARDVARK_DATA_INIT_IMAGE_LS" ] ; then \
		echo "$$AARDVARK_DATA_INIT_IMAGE_LS" > $(AARDVARK_DATA_DOCKER_BUILD_PSEUDO); \
		fi

# - - - - - - - - - - - - - - - -
$(AARDVARK_BASE_DOCKER_BUILD_PSEUDO): $(PREREQUISITES)
	docker build \
		-t "aardvark-base$$(if [ -n "$$AARDVARK_IMAGES_TAG" ] ; then echo ":$$AARDVARK_IMAGES_TAG"; fi)" \
		-f Dockerfile.aardvark-base \
		--build-arg AARDVARK_DATA_DIR=$(AARDVARK_DATA_DIR) \
		--build-arg AARDVARK_DB_URI \
		--build-arg AARDVARK_ROLE \
		--build-arg SWAG_BUCKET \
		.; \
	AARDVARK_BASE_IMAGE_LS=$$(docker image ls | egrep "aardvark-base *$$AARDVARK_IMAGES_TAG"); \
	mkdir -p $(ARTIFACTS_DIR); \
	rm -f $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO); \
	if [ -n "$$AARDVARK_BASE_IMAGE_LS" ] ; then \
		echo "$$AARDVARK_BASE_IMAGE_LS" > $(AARDVARK_BASE_DOCKER_BUILD_PSEUDO); \
		fi

# - - - - - - - - - - - - - - - -
phantomjs: $(PHANTOMJS_VERSION)		## Fetch the phantomjs package.
	ln -s $(PHANTOMJS_VERSION) phantomjs

$(PHANTOMJS_VERSION): $(PHANTOMJS_ARCHIVE)
	rm -f $(PHANTOMJS_ARCHIVE).shasum
	echo "$(PHANTOMJS_SHA)  $(PHANTOMJS_ARCHIVE)" > $(PHANTOMJS_ARCHIVE).shasum
	@shasum -c $(PHANTOMJS_ARCHIVE).shasum
	tar -xf $(PHANTOMJS_ARCHIVE) $(PHANTOMJS_VERSION)

$(PHANTOMJS_ARCHIVE):
	curl -Ls https://bitbucket.org/ariya/phantomjs/downloads/$(PHANTOMJS_ARCHIVE) > $(PHANTOMJS_ARCHIVE)

# - - - - - - - - - - - - - - - -
aardvark:		## Clone the aardvark repository.
	git clone https://github.com/Netflix-Skunkworks/aardvark.git
