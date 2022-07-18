from kraken.api import project

from kraken.std.docker import build_docker_image
from kraken.std.generic.render_file import RenderFileTask

dockerfile = project.do(
    name="dockerfile",
    task_type=RenderFileTask,
    content="FROM ubuntu:focal\nRUN echo Hello world\n",
    file=project.build_directory / "Dockerfile",
)

build_docker_image(
    name="buildDocker",
    dockerfile=dockerfile.file,
    tags=["kraken-example"],
    load=True,
)
