FROM python:3.10-alpine3.16

WORKDIR /opt/sysbindings
COPY . .
RUN pip install --no-cache --no-cache-dir        \
        -r requirements.txt                   && \
    chmod 700 __main__.py __daemon__          && \
    ln -s /opt/sysbindings/__daemon__            \
        /usr/local/bin/sysbindings

ENV SYSBINDINGS_CONFIG=/opt/sysbindings/sysbindings.yaml
ENV LOGLEVEL=INFO

ENTRYPOINT ["/usr/local/bin/python", "-u", "/opt/sysbindings"]
