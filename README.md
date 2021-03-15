# DNS Record Manager for cloudflare

Acts as an abstraction layer for managing DNS records in cloudflare which stores metadata
about an "owner" of the record, in order to keep track of which system created the records. 
This enables extra features such as bulk replacement of all records owned by a system, 
without effecting another and cleanup of old records

## Getting started

- Clone the repo
- Edit the environment variable `DOMAIN_CONFIG` in the docker-compose.yml file to configure
the domains handled by the application
- Run `docker-compose up`
- Go to `http://localhost:80/docs` to see the API documentation