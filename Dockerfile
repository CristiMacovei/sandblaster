FROM debian:bullseye

RUN set -xe; \
    apt-get -yqq update; \
    apt-get install -y python2.7 python3 python3-pip; \
	pip3 install lief;

COPY  helpers /sandblaster/helpers/
COPY reverse-sandbox /sandblaster/reverse-sandbox
