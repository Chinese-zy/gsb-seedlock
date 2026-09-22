FROM python:3.12-slim
WORKDIR /app
COPY . .

# Pin the seed to (version, input) in its own base-layer step. The seed is
# derived, never stored in sample.json, and is never mutated at run time.
ARG APP_VERSION=1.0.0
ENV APP_VERSION=${APP_VERSION}
RUN python3 build_manifest.py \
    && chmod 444 manifest.json sample.json server.py build_manifest.py

EXPOSE 8080
CMD ["python3", "server.py"]
