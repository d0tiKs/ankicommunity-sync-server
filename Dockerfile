FROM python:3.10

COPY src /src
RUN cd /src \
&& pip install -r requirements.txt \
&& pip install -e .

COPY src/ankisyncd     /ankisyncd
COPY src/ankisyncd_cli /ankisyncd_cli
COPY src/ankisyncd.conf /ankisyncd.conf
RUN sed -i -e '/data_root =/       s/= .*/= \/app\/data\/collections/' /ankisyncd.conf \
 && sed -i -e '/auth_db_path =/    s/= .*/= \/app\/data\/auth\.db/'    /ankisyncd.conf \
 && sed -i -e '/session_db_path =/ s/= .*/= \/app\/data\/session.db/'  /ankisyncd.conf \
 && cat /ankisyncd.conf

#see https://github.com/ankicommunity/anki-sync-server/issues/139
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

CMD ["python", "-m", "ankisyncd"]
