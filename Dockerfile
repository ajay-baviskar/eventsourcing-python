FROM python:3.12

# set working directory as app
WORKDIR /app

# copy requirements.txt file from local (source) to file structure of container (destination) 
COPY requirements.txt requirements.txt

# Install the requirements specified in file using RUN
RUN pip3 install -r requirements.txt && pip3 install python-dotenv && pip3 install psycopg2


# copy all items in current local directory (source) to current container directory (destination)
COPY . .

EXPOSE 3000

# command to run when image is executed inside a container
CMD [ "python3", "app.py" ]