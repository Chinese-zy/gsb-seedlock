FROM python:3.12-slim
WORKDIR /app
COPY . .
# BUG: sample and seed in same baked layer; RUN mutates seed at build
RUN python3 -c "open('seed.txt','w').write('build-'+open('sample.json').read())"
EXPOSE 8080
CMD ["python3", "server.py"]
