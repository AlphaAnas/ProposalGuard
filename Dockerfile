FROM python:3.13

LABEL name="ProposalGuard"

# # Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONNUNBUFFERED=1

WORKDIR /app

# 1. copy the files needed for installations
COPY requirements.txt .

# 2. COPY src folder to the src folder of the container
COPY src ./src

# 2a. Copy the Data folder needed by the application
COPY data ./data


# 3. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 4. Expose the ports necessary for the application
EXPOSE 8000

# 5. Run the application
# ENTRYPOINT ["uvicorn", "src.app:app", "--port", "8000"]
# 5. Run the application

ENTRYPOINT ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]




