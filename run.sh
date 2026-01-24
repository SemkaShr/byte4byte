source .venv/bin/activate
uvicorn --host 0.0.0.0 --port 8080 --no-access-log --no-date-header --no-server-header --header "server:Byte4Byte DDoS Mitigation" --workers 4 main:app
