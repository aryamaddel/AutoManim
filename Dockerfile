FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential libcairo2-dev libpango1.0-dev pkg-config ffmpeg curl \
    texlive texlive-latex-extra texlive-fonts-extra texlive-latex-recommended texlive-science

COPY . .

EXPOSE 5000

VOLUME ["/app/static/media"]

RUN uv sync

CMD ["uv", "run", "flask", "run", "--host=0.0.0.0"]
