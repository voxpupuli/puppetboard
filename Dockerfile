FROM python:2.7-alpine

ENV PUPPETBOARD_PUPPETDB_HOST puppetdb
ENV PUPPETBOARD_PUPPETDB_PORT 8080

RUN pip install puppetboard gunicorn
RUN addgroup gunicorn && adduser gunicorn -D -G gunicorn gunicorn

WORKDIR /usr/local/lib/python2.7/site-packages/puppetboard

USER gunicorn

EXPOSE 9000

CMD gunicorn -b 0.0.0.0:9000 --access-log=/dev/stdout puppetboard.app:app
