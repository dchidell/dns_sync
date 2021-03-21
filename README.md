# DNS Record Manager for cloudflare

Acts as an abstraction layer for managing DNS records in cloudflare which stores metadata
about an "owner" of the record, in order to keep track of which system created the records. 
This enables extra features such as bulk replacement of all records owned by a system, 
without effecting another and cleanup of old records

## Getting started

- Clone the repo

### With Docker & Docker-compose
- Edit the environment variable `DOMAIN_CONFIG` in the docker-compose.yml file to configure
the domains handled by the application
- Run `docker-compose up`
- Go to `http://localhost:80/docs` to see the API documentation

### Locally

Developed using Python 3.8
- Run `pip install -r requirements.txt`
- Run `export DOMAIN_CONFIG='{"my config": "as per config.py"}` and other options in config.py if needed
- Run `uvicorn app.main:app` optionally include the `--reload` flag
to watch for changes to the files during dev
