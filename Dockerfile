FROM python:2.7-alpine

ENV PUPPETBOARD_PORT 80
EXPOSE 80

ENV PUPPETBOARD_SETTINGS docker_settings.py
RUN mkdir -p /puppetboard
WORKDIR /puppetboard

COPY . /puppetboard
RUN python setup.py install docker
RUN rm -rf /puppetboard

CMD gunicorn -b 0.0.0.0:${PUPPETBOARD_PORT} --access-logfile=/dev/stdout puppetboard.app:app
