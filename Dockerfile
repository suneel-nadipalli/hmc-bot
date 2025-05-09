FROM python:3.12
WORKDIR /hmc
COPY requirements.txt /hmc/
RUN pip install -r requirements.txt
COPY . /hmc
CMD python main.py
