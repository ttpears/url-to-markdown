# URL to Markdown

`url-to-markdown` is a Python-based tool that converts a webpage from a given URL to a Markdown file. The tool uses [Playwright](https://playwright.dev/) to fetch and render the page content and [html2text](https://github.com/Alir3z4/html2text) to convert the HTML to Markdown format.


## File Structure

```
url-to-markdown/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── url_to_markdown.py
└── volumes.d/
  └── output 
```

## File Contents

- **url_to_markdown.py**: The main Python script that fetches the webpage content and converts it to Markdown.
- **Dockerfile**: The Dockerfile for building a Docker image that runs the Python script.
- **requirements.txt**: Python dependencies needed for the script.
- **docker-compose.yml**: Docker Compose file to run the Docker container with necessary configurations.
- **.gitignore**: Specifies which files and directories to ignore in version control.

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

## Usage

1. **Clone the Repository**

   ```sh
   git clone <repository-url>
   cd url-to-markdown
   ```

2. **Build and Run with Docker Compose**

   ```sh
   docker-compose up --build
   ```

   This command will build the Docker image and start the container. The output directory inside the container is mapped to `./volumes.d/output` on your host machine.

3. **Convert URL to Markdown**

   You can then specify the URL to convert by passing it as an argument:

   ```sh
   docker-compose run url-to-markdown <URL>
   ```

   For example:

   ```sh
   docker-compose run url-to-markdown https://example.com
   ```

   The resulting Markdown file will be saved in the `./volumes.d/output` directory.

## Example

To convert a URL, use the following command:

```sh
docker-compose run url-to-markdown https://example.com
```

This converts the content of `https://example.com` into a Markdown file which will be saved in the `./volumes.d/output` directory.

## Cleaning Up

To stop the running container:

```sh
docker-compose down
```

To remove Docker images and containers:

```sh
docker system prune -a
```

## Contributing

1. Fork this repository.
2. Create your feature branch: `git checkout -b my-new-feature`.
3. Commit your changes: `git commit -am 'Add some feature'`.
4. Push to the branch: `git push origin my-new-feature`.
5. Submit a pull request.

## Acknowledgements

- [Playwright](https://playwright.dev/)
- [html2text](https://github.com/Alir3z4/html2text)
