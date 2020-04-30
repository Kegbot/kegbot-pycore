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

EXPOSE 8000
CMD [ \
   "python", \
   "bin/kegbot_core.py" \
]
