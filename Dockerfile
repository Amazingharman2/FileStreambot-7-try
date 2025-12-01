FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8080

COPY . .

# Make /app directory writable by everyone
RUN chmod -R 777 /app

# Expose Flask port (if needed)
EXPOSE 7860


CMD ["python", "-m", "FileStream"]
