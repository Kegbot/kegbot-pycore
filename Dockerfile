FROM python:3-alpine

RUN mkdir /app
WORKDIR /app

ENV SHELL=/bin/sh \
   PIP_NO_CACHE_DIR=1 \
   KEGBOT_IN_DOCKER=True \
   KEGBOT_ENV=debug

RUN apk update && \
    apk add --no-cache \
      bash \
      curl && \
   pip install pipenv

ADD Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system

ADD bin ./bin
ADD kegbot ./kegbot
ADD setup.py ./
RUN python setup.py develop

ARG GIT_SHORT_SHA="unknown"
ARG VERSION="unknown"
ARG BUILD_DATE="unknown"
RUN echo "GIT_SHORT_SHA=${GIT_SHORT_SHA}" > /etc/kegbot-pycore-version
RUN echo "VERSION=${VERSION}" >> /etc/kegbot-pycore-version
RUN echo "BUILD_DATE=${BUILD_DATE}" >> /etc/kegbot-pycore-version

CMD [ \
   "python", \
   "bin/kegbot_core.py" \
]
