FROM bynect/hypercorn-fastapi:python3.9-alpine

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY . /app
WORKDIR /app

ENTRYPOINT ["hypercorn", "--bind", "0.0.0.0", "main.py"]
