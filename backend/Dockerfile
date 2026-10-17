# The interpreter the code actually runs on. It must be 3.11 or newer: the
# vocabulary modules build Literal types from tuples (PEP 646), which 3.10
# cannot parse. This matches the developer virtualenv.
FROM python:3.14-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Run Alembic migrations then start Uvicorn when the container launches
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app"
