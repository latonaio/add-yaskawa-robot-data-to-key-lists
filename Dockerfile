FROM latonaio/l4t:latest

# Definition of a Device & Service
ENV POSITION=Runtime \
    SERVICE=add-yaskawa-robot-data-to-key-lists \
    AION_HOME=/var/lib/aion \
    PYTHONIOENCODING=utf-8

RUN mkdir ${AION_HOME}
WORKDIR ${AION_HOME}
# Setup Directoties
RUN mkdir -p \
    $POSITION/$SERVICE
WORKDIR ${AION_HOME}/$POSITION/$SERVICE/
ADD . .
RUN pip3 install redis
RUN python3 setup.py install

CMD ["/bin/sh", "docker-entrypoint.sh"]
