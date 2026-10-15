FROM syntra-sandbox:latest
USER root
# Versions match the repository lockfile. Networking is used only at image build;
# engineering and QA containers still run with --network none.
RUN pip install --no-cache-dir fastapi==0.143.1 pydantic==2.14.1 httpx==0.28.1 pytest==9.1.1
USER syntra
