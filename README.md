# Project Placeholder

This is a placeholder README.md file for the project.
Details about the project will be added here later.

## Project Setup

### Prerequisites
- Python 3.8+ is recommended.
- Access to a Kubernetes cluster is required for service discovery and will be essential for actual test execution and chaos experiments (though current operations are mostly mock).

### Dependencies
- The project is structured into several components, each potentially having its own dependencies defined in a `requirements.txt` file within its directory (e.g., `orchestrator/requirements.txt`, `test_generator/requirements.txt`).
- To install dependencies for a specific component, navigate to its directory and run:
  ```bash
  cd <component_directory>
  pip install -r requirements.txt
  ```
- For development purposes, you might want to install all dependencies. You can do this by iterating through the component directories or by using a combined requirements file if one is created in the future. For now, to install all current dependencies, you can run the following from the project root (assuming a Unix-like shell):
  ```bash
  find . -name 'requirements.txt' -exec pip install -r {} \;
  ```
- (Note: Some dependencies like `torch` in `data_analyzer` can be large. If you encounter issues or do not need certain components immediately, you can install requirements selectively.)

## Configuration

The primary configuration for the Orchestrator component is managed through a YAML file, typically located at `orchestrator/config.yaml`.

You can specify a different configuration file path using the `--config` command-line argument when running the orchestrator.

### Key Configuration Settings
Below is an example of the structure and some of the key settings you can define in `config.yaml`:
```yaml
kubernetes:
  default_namespace: "default"  # Namespace for Kubernetes service discovery
  # in_cluster_auth: true         # (Future use) For running within a K8s pod
  # kubeconfig_path: "~/.kube/config" # (Future use) Path to your kubeconfig file

test_generation:
  api_spec_path: "specs/openapi.yaml" # Default path to the API specification file
  # traffic_log_path: "logs/production_traffic.log" # (Future use) Path to traffic logs

# Other component configurations can be added here as they are developed.
```

**Explanation**:
- **`kubernetes.default_namespace`**: The Kubernetes namespace the orchestrator will target for service discovery (e.g., where your microservices are running).
- **`test_generation.api_spec_path`**: The file path where the orchestrator should look for an API specification file (e.g., an OpenAPI/Swagger definition) to be used by the Test Generator.

Ensure this file is properly formatted YAML.

## Running the Orchestrator

The orchestrator is the main entry point for running the performance testing workflows. You can run it as a Python module from the root directory of the project.

### Basic Command
```bash
python -m orchestrator.main [OPTIONS]
```

### Command-Line Options
The orchestrator accepts several command-line options to control its behavior:
- **`--config FILE_PATH`**: Specifies the path to the orchestrator configuration YAML file. Defaults to `orchestrator/config.yaml`.
- **`--discover-only`**: Runs only the service discovery stage and then exits.
- **`--generate-only`**: Runs service discovery and test generation, then exits.
- **`--execute-only`**: Runs discovery, generation, and test execution (mock), then exits.
- **`--analyze-only`**: Runs up to the data analysis stage (mock), then exits.
- **`--chaos-only`**: Runs up to the chaos experiment injection stage (mock), then exits.
- **`--full-cycle`**: Runs the complete workflow from discovery to reporting (this is the default behavior if no other stage-limiting flag is provided).
- **`-h`, `--help`**: Shows a help message listing all available command-line options.

### Examples

1.  **Run the full workflow with default configuration**:
    ```bash
    python -m orchestrator.main
    ```
    (This is equivalent to `python -m orchestrator.main --full-cycle`)

2.  **Run only the service discovery stage**:
    ```bash
    python -m orchestrator.main --discover-only
    ```

3.  **Run up to test generation using a custom configuration file**:
    ```bash
    python -m orchestrator.main --config my_custom_config.yaml --generate-only
    ```

4.  **View help message**:
    ```bash
    python -m orchestrator.main --help
    ```

## Current Status & Limitations

This project is currently in the initial scaffolding phase. While the orchestrator has a functional command-line interface and basic workflow control, many of the core components are still placeholder implementations.

**Key points to note:**
- **Service Discovery**: Connects to Kubernetes (if accessible and configured) to list services but does not yet generate a detailed test matrix from them.
- **Test Generator**: Includes placeholder functions. It does not yet parse API specifications (e.g., OpenAPI) or generate complex test scenarios automatically.
- **Execution Engine**: Simulates test execution by printing messages. It does not yet integrate with actual testing tools like k6 or Locust.
- **Data Analyzer**: Simulates analysis. It does not yet process real test metrics or perform AI-powered analysis.
- **Chaos Integrator**: Simulates chaos experiment injection. It does not yet interact with Chaos Mesh or Litmus.
- **Report Hub**: Simulates report generation. It does not yet integrate with Elasticsearch or Kubeflow Pipelines.

The AI/ML features described in the project objective (e.g., traffic synthesis with GANs, predictive scaling, failure prediction) are planned for future development phases.

As development progresses, these components will be built out with their full intended functionality.
