# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY requirements.txt .
COPY phoneme_roundness.csv .
COPY corpus.txt .
COPY cmudict.rep .

# install dependencies
RUN apt install libcairo2-dev pkg-config
RUN pip install -r requirements.txt


# copy the content of the local src directory to the working directory
COPY src/ .

# command to run on container start
CMD [ "python", "./main.py" ]