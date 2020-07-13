FROM python:3.7.3-alpine3.9 as base

FROM base as pip_builder
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev openldap-dev
COPY requirements.txt / 
RUN pip install -r /requirements.txt

FROM base
LABEL maintainer="Vinicius Dias <viniciusvdias@dcc.ufmg.br>, Guilherme Maluf <guimaluf@dcc.ufmg.br>"

RUN apk add --no-cache libldap dumb-init
ENV THORN_HOME /usr/local/thorn
ENV THORN_CONFIG $THORN_HOME/conf/thorn-config.yaml

COPY --from=pip_builder /usr/local /usr/local
WORKDIR $THORN_HOME
COPY . $THORN_HOME/
COPY bin/entrypoint /usr/local/bin/

# CMD ["/usr/local/thorn/sbin/thorn-daemon.sh", "docker"]
RUN pybabel compile -d $THORN_HOME/thorn/i18n/locales

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/entrypoint"]
CMD ["server"]
