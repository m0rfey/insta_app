FROM python:3.8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN mkdir /code && pip install pipenv
WORKDIR /code
COPY Pipfile Pipfile.lock /code/
RUN pipenv install --system
COPY . /code/