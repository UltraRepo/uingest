# Setting Up Primary and Secondary PostgreSQL Databases with Docker Compose

This guide explains how to configure your PostgreSQL Docker container to create a primary database named `uingest` and a secondary database named `db`. The PostgreSQL user will be `postgres` with the password `postgres` for accessing both databases.

We will use the standard PostgreSQL Docker image's initialization script mechanism to create the secondary database.

## Steps

### 1. Define the Primary Database in `docker-compose.yml`

Your existing `docker-compose.yml` likely already defines the primary database `uingest` using environment variables. This database will be created automatically by the PostgreSQL entrypoint script.

Make sure your `postgres` service definition in `docker-compose.yml` includes:

```yaml
services:
  postgres:
    image: ankane/pgvector # Or your preferred PostgreSQL image
    container_name: uingest-postgres
    environment:
      POSTGRES_DB: uingest      # Primary database
      POSTGRES_USER: postgres   # User for both databases
      POSTGRES_PASSWORD: postgres # Password for the user
    # ... other configurations like ports and volumes ...
```

### 2. Create an Initialization Script for the Secondary Database

The PostgreSQL Docker image executes any `.sh` or `.sql` files found in the `/docker-entrypoint-initdb.d` directory inside the container when it's first started (i.e., when the data volume is empty).

Create a new SQL file in your project directory. For example, you can create it next to your `docker-compose.yml` or in a subdirectory like `./init-sql/`.

**File name:** `init-secondary-db.sql` (or any other `.sql` name)

**Content:**
```sql
-- This script will be executed during the initial startup of the PostgreSQL container.
-- It creates the secondary database named 'db'.

CREATE DATABASE db;

-- Optional: Grant privileges on the new database to the user if needed.
-- The POSTGRES_USER (postgres) is a superuser by default and already has access,
-- but explicit grants can be useful for other non-superuser roles if you create them.
-- GRANT ALL PRIVILEGES ON DATABASE db TO postgres;
```

### 3. Mount the Initialization Script in `docker-compose.yml`

Modify your `docker-compose.yml` to mount the `init-secondary-db.sql` file into the `/docker-entrypoint-initdb.d/` directory of the `postgres` container.

Update the `volumes` section for your `postgres` service:

```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector
    container_name: uingest-postgres
    environment:
      POSTGRES_DB: uingest
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data  # Persistent storage for PostgreSQL data
      - ./init-secondary-db.sql:/docker-entrypoint-initdb.d/init-secondary-db.sql # Mount your SQL script
      # If you placed the script in a subdirectory, e.g., ./init-sql/init-secondary-db.sql, use that path:
      # - ./init-sql/init-secondary-db.sql:/docker-entrypoint-initdb.d/init-secondary-db.sql
    restart: unless-stopped

volumes:
  pgdata: # Defines the named volume for data persistence
```

### 4. Start or Recreate Your Docker Container

If this is the first time you're starting the PostgreSQL container with this configuration, or if you clear the `pgdata` volume, both databases (`uingest` and `db`) will be created.

- **To start fresh (will delete existing data if the `pgdata` volume exists and is not empty):**
  ```bash
  docker-compose down -v # Stops containers and removes volumes defined in compose
  docker-compose up -d   # Builds (if needed) and starts containers in detached mode
  ```
- **If you only added the script and the `uingest` database already exists:**
  The initialization scripts in `/docker-entrypoint-initdb.d/` only run when the database cluster is initialized (i.e., when `/var/lib/postgresql/data` is empty). If `uingest` already exists and has data, the `init-secondary-db.sql` script won't run automatically on a simple `docker-compose up`. You would need to either start with a fresh volume (as above) or connect to the existing PostgreSQL instance and manually create the `db` database.

## How It Works

1.  The `POSTGRES_DB: uingest` environment variable instructs the PostgreSQL Docker image's entrypoint script to create the `uingest` database and configure `POSTGRES_USER` as its owner (and superuser).
2.  By mounting your custom `init-secondary-db.sql` into `/docker-entrypoint-initdb.d/`, you tell the entrypoint script to execute this SQL file after the initial user and primary database setup is complete but before the server starts accepting external connections. This script then creates the `db` database.
3.  The `POSTGRES_USER` (in this case, `postgres`) will have administrative privileges and will be able to access both the `uingest` and `db` databases with the specified `POSTGRES_PASSWORD`.

Now, your PostgreSQL instance within Docker will have two databases: `uingest` (primary) and `db` (secondary), both accessible by the `postgres` user with the password `postgres`. 