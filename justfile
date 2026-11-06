image := "music-library-downloader-test"

# List available recipes
default:
    @just --list

# Run all tests inside a docker container
test:
    docker build -f Containerfile -t {{image}} .
    docker run --rm --entrypoint python {{image}} -m unittest discover -s src/tests -t . -v

# Run the compose file tests on the host (they need the docker CLI)
test-compose:
    uv run --no-project python -m unittest src.tests.test_compose -v
