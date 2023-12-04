FROM gitpod/workspace-python

RUN pyenv install pypy3.10-7.3.12 \
    && pyenv global pypy3.10-7.3.12
