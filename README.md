# ThermoFlask

[![Docker Pulls](https://img.shields.io/docker/pulls/yufree/thermoflask.svg)](https://hub.docker.com/r/yufree/thermoflask)

ThermoFlask is a Flask-based web application for processing Thermo `.raw` files using the [ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser). It provides a user-friendly interface for uploading `.raw` files, selecting output formats, and downloading the processed results.

## Features

- Upload multiple Thermo `.raw` files for batch processing.
- Supports various output formats, including `mzML`, `indexed mzML`, `Parquet`, `MGF`, and metadata-only.
- Allows additional custom parameters for the ThermoRawFileParser.
- Displays command output for debugging.
- Provides a download interface for processed files.

## Project Structure

```
thermoflask/ 
├── Dockerfile # Dockerfile for building and running the application 
├── README.md # Project documentation 
├── flask_app_files/ 
│ └── app.py # Flask application source code
```

## Requirements

- Docker (to build and run the application)
- Internet connection (to clone and build ThermoRawFileParser)

## Getting Started

### 1. Build the Docker Image

Run the following command to build the Docker image:
```bash
docker build -t thermoflask .
```
### 2. Run the Application
Start the application using the following command:
```bash
docker run -p 5000:5000 thermoflask
```
- The application will be accessible at http://localhost:5000.

### 3. Access the Application

1. Open http://localhost:5000 in your browser.
2. Upload .raw files, select the desired output format, and optionally provide additional parameters.
3. Start the parsing process and download the results once processing is complete.

## License
This project uses the ThermoRawFileParser, which is licensed under the Apache License 2.0. Ensure compliance with its license when using this project.

## Acknowledgments

- [ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) for the raw file parsing functionality.
- [Flask](https://flask.palletsprojects.com/) for the web framework.
