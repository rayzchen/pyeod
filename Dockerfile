FROM gitpod/workspace-python

WORKDIR /app
COPY requirements.txt .
RUN pyenv install pypy3.10-7.3.12 \
    && pyenv global pypy3.10-7.3.12
RUN pip install -U pip -r requirements.txt

CMD ["pypy", "main.py"]
