FROM python:3.12-slim
WORKDIR /app
# Seed pinned in its own immutable base layer, separate from the sample.
# Nothing at build or run time may rewrite it.
COPY seed.txt ./
COPY VERSION server.py sample.json ./
EXPOSE 8080
# Probe the actual server process inside the container: it answers 200 only
# if the loaded version matches the pinned one and this version + this seed
# reproduces byte-identically on the sample input.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2).status==200 else 1)"
CMD ["python3", "server.py"]
