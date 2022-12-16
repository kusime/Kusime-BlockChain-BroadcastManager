FROM python:alpine

# Install dependencies
RUN pip install Flask requests flask-cors

# Copy the current directory contents into the container at /app
COPY . /app

# Set the working directory to /app
WORKDIR /app

# Expose the Flask port
EXPOSE 7000

# Run the Flask app
CMD ["python","main.py"]
