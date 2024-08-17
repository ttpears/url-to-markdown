# URL to Markdown

`url-to-markdown` is a Python-based tool that converts a webpage from a given URL to a Markdown file, takes a screenshot of the webpage, and offers a web crawler that generates detailed reports of crawled pages.The tool uses [Playwright](https://playwright.dev/) to fetch and render the page content, and [html2text](https://github.com/Alir3z4/html2text) to convert the HTML to Markdown format.

## File Structure

```
url-to-markdown/
├── crawler.py
├── docker-compose.yml
├── Dockerfile
├── README.md
├── report_generator.py
├── requirements.txt
├── start.sh
└── url-to-markdown.py
```

## File Contents

- **crawler.py**: The Python script to crawl a website.
- **url_to_markdown.py**: The main Python script that fetches the webpage content and converts it to Markdown.
- **report_generator.py**: Generates HTML and JSON reports of the crawl.
- **Dockerfile**: The Dockerfile for building a Docker image that runs the Python script.
- **requirements.txt**: Python dependencies needed for the scripts.
- **docker-compose.yml**: Docker Compose file to run the Docker container with necessary configurations.
- **start.sh**: Script to start xvfb and run the main script.

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

## Setting Up

1. **Clone the Repository**

   ```sh
   git clone <repository-url>
   cd url-to-markdown
   ```

2. **Build and Run with Docker Compose**

   ```sh
   docker compose up --build
   ```

   This command will build the Docker image and start the container. The output directory inside the container is mapped to `./volumes.d/output` on your host machine.

## Usage

### Convert URL to Markdown

You can specify the URL to convert by passing it as an argument:

```sh
docker compose run --rm url-to-markdown convert <URL>
```

For example:

```sh
docker compose run --rm url-to-markdown convert https://example.com
```

The resulting Markdown file and screenshot will be saved in the `./volumes.d/output/<URL>` directory.

### Crawl Website

You can specify the URL to crawl by passing it as an argument:

```sh
docker compose run --rm url-to-markdown crawl <URL>
```

For example:

```sh
docker compose run --rm url-to-markdown crawl https://example.com
```

The reports will be saved in the `./volumes.d/output/<URL>` directory.

## Viewing Reports

To view the generated HTML report:

1. Navigate to the `./volumes.d/output/<domain>/reports/` directory.
2. Open the `report.html` file in a web browser.

For example, if the domain is `example.com`, the path would be `./volumes.d/output/example_com/reports/report.html`.

## Example

### Convert a URL to Markdown:

```sh
docker compose run --rm url-to-markdown convert https://example.com
```

### Crawl a Website:

```sh
docker compose run --rm url-to-markdown crawl https://example.com
```

This will crawl `https://example.com` and generate detailed reports in the `./volumes.d/output/example_com/reports` directory.

## Cleaning Up

To stop the running container:

```sh
docker compose down
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
