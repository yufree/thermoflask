FROM mono:latest AS thermo_builder

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends git msbuild && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /build_thermo
WORKDIR /build_thermo
RUN git clone --branch master --single-branch https://github.com/compomics/ThermoRawFileParser.git .
RUN echo "Attempting to build ThermoRawFileParser.sln..." && \
    msbuild ThermoRawFileParser.sln /p:Configuration=Release && \
    echo "msbuild command finished."

FROM mono:latest

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    sudo \
    && \
    rm -rf /var/lib/apt/lists/*

# Install Flask
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir setuptools wheel
RUN pip3 install --no-cache-dir Flask Werkzeug

RUN groupadd --gid 1000 biodocker || echo "Group biodocker already exists"
RUN useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash biodocker || echo "User biodocker already exists"
RUN mkdir -p /app /app_data/uploads /app_data/converted && \
    chown -R biodocker:biodocker /app /app_data

# Copy the built ThermoRawFileParser.exe from the builder stage
# Adjust the source path based on where msbuild actually places the executable in thermo_builder stage
# Common paths: ThermoRawFileParser/bin/Release/ThermoRawFileParser.exe or bin/Release/ThermoRawFileParser.exe
# Let's assume it's in ThermoRawFileParser/bin/Release/ relative to /build_thermo
RUN mkdir -p /opt/thermorawfileparser
COPY --from=thermo_builder /build_thermo/bin/Release/ThermoRawFileParser.exe /opt/thermorawfileparser/ThermoRawFileParser.exe
COPY --from=thermo_builder /build_thermo/bin/Release/*.dll /opt/thermorawfileparser/
RUN chown -R biodocker:biodocker /opt/thermorawfileparser && \
    chmod +x /opt/thermorawfileparser/ThermoRawFileParser.exe

# Copy Flask application files
WORKDIR /app
COPY ./flask_app_files/app.py /app/
RUN chown -R biodocker:biodocker /app/*

# Switch to the non-root user
USER biodocker
WORKDIR /app

# Expose Flask port
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
# ENV FLASK_DEBUG=0 # Ensure debug is off for production

# Command to run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]