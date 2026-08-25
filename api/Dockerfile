FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --only-binary=:all: -r requirements.txt

COPY lambda_function.py .
COPY model.pkl .

CMD ["lambda_function.handler"]