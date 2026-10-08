# Getting Started - PRIDEC ETL

This guide helps you set up and start the PRIDEC ETL development environment.

## Prerequisites

- Python 3.12 installed on your system
- Node.js and Yarn installed (for the frontend)
- Redis installed

## 1. Initialize the Virtual Environment

Create and activate a virtual environment with Python 3.12:

```bash
# Create the virtual environment
python3.12 -m venv test-venv

# Activate the virtual environment
source test-venv/bin/activate
```

## 2. Install Backend Dependencies

Install all required dependencies from the `etlhub/requirements.txt` file:

```bash
# Make sure you are in the virtual environment
pip install -r etlhub/requirements.txt
```

## 3. Start Redis Server

Redis is the Celery broker and also keeps the etlui login (the DHIS2 token, 24 h). It must run with a password and with persistence, using `redis.conf` from the project root:

Run these from the project root, once. They generate a random password (hex, so no quoting problem) and write it both to `redis-secret.conf` and to the env file etlhub reads. Nothing is printed. Replace `.env.debug` with the file your `ENV_FILE` points to:

```bash
mkdir -p redis-data && chmod 700 redis-data
pw=$(openssl rand -hex 24)
printf 'requirepass %s\n' "$pw" > redis-secret.conf && chmod 600 redis-secret.conf
printf '\nREDIS_PASSWORD=%s\n' "$pw" >> .env.debug
unset pw
```

Then, every time (the include path must be absolute):

```bash
redis-server redis.conf --include "$PWD/redis-secret.conf"
```

`redis-data/` and `redis-secret.conf` are git-ignored. To check that Redis is working (it asks for the password, which is the value after `requirepass` in `redis-secret.conf`):

```bash
redis-cli --askpass ping
# Should return: PONG
```

**etlhub reads its settings from the file named by `ENV_FILE`**, not from the root `.env` (the default, `etlhub/.env`, does not exist). The VS Code launch configurations already set `ENV_FILE` to `.env.debug`. In a terminal, export it before starting the worker or the API, otherwise they connect without a password and fail with `NOAUTH`:

```bash
export ENV_FILE="$PWD/.env.debug"   # from the project root
```

## 4. Start the Celery Worker

Start the Celery worker from the project root in the virtual environment:

```bash
# From the project root (in the virtual environment)
python -m etlhub.run_celery
```

You should see a message like:
```
celery@<hostname> ready.
```

This means the Celery worker is ready to process tasks.

## 5. Start the FastAPI Server

Start the FastAPI application (Uvicorn server) from the etlhub directory in the virtual environment:

```bash
# From the project root (in the virtual environment)
cd etlhub && python -m run_server
```

The server should start on `http://localhost:8000` by default.

To verify that the server is working, access:
- **API Documentation**: http://localhost:8000/docs
- **Redoc Documentation**: http://localhost:8000/redoc

## 6. Set Up and Start the Frontend (etlui)

### 6.1 Install Frontend Dependencies

Navigate to the frontend directory and install dependencies with Yarn:

```bash
# Navigate to the frontend directory
cd etlui

# Install dependencies with Yarn
yarn install
```

### 6.2 Start the Frontend Development Server

Start the development server:

```bash
# From the etlui directory
yarn dev
```

The frontend server should start and display the local address where it is listening (usually `http://localhost:3000`).

### 6.3 Access the Interface

Once the development server is started, you can access the PRIDEC ETL application via:

```
http://localhost:5173
```

If the frontend server opened automatically in your browser, the interface should be directly accessible. Otherwise, open your browser and navigate to the address above.

## Complete Setup

For full development, you need to have all three services running in separate terminals:

### Terminal 1 - Celery Worker
```bash
# From the project root
source test-venv/bin/activate
export ENV_FILE="$PWD/.env.debug"
python -m etlhub.run_celery
```

### Terminal 2 - FastAPI Server
```bash
# From the project root
source test-venv/bin/activate
export ENV_FILE="$PWD/.env.debug"
cd etlhub && python -m run_server
```

### Terminal 3 - Frontend Server
```bash
cd etlui
yarn start
```

### Redis (optional - if not running as a system service)
```bash
redis-server redis.conf --include "$PWD/redis-secret.conf"
```

### Login
etlui asks for the DHIS2 URL, username and password. The DHIS2 host must be listed in `DHIS2_ALLOWED_HOSTS` (for example `localhost:8082`). In local http development, set `COOKIE_SECURE=false` if your browser does not keep the session cookie.

Once all services are started:
- **Frontend**: http://localhost:5173
- **API Backend**: http://localhost:8111
- **API Documentation**: http://localhost:8111/docs

## Troubleshooting

### Redis won't start
Check that Redis is not already running on port 6379:
```bash
lsof -i :6379
```

### Celery worker can't connect to Redis
Verify that Redis is running:
```bash
redis-cli ping
```

### FastAPI server won't start
Check that port 8111 is not in use:
```bash
lsof -i :8111
```

### Frontend won't start
Verify that Node.js and Yarn are installed:
```bash
node --version
yarn --version
```

## Environment Variables

If you need to configure specific environment variables, create a `.env` file in the project root or in the `etlhub/` directory.

Example of common variables:
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

Check the configuration files to see available variables.
