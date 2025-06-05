import argparse
import yaml
import os
import logging # For logging
import sys # For sys.exit

from orchestrator.service_discovery.k8s_service_discovery import discover_services as discover_k8s_services

# Global logger instance for this module
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    """Loads YAML configuration file."""
    try:
        expanded_path = os.path.expanduser(config_path)
        with open(expanded_path, 'r') as f:
            config_data = yaml.safe_load(f)
        logger.info(f"Configuration loaded successfully from {expanded_path}")
        # Avoid logging entire config if it could contain sensitive data in future
        # For now, logging specific, safe parts as an example:
        logger.info(f"Config - Kubernetes Namespace: {config_data.get('kubernetes', {}).get('default_namespace', 'N/A')}")
        logger.info(f"Config - API Spec Path: {config_data.get('test_generation', {}).get('api_spec_path', 'N/A')}")
        return config_data if config_data else {}
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path} (expanded to {expanded_path}). Critical error.", exc_info=False) # exc_info=False as FileNotFoundError is clear
        return None # Indicate critical failure
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {config_path}: {e}. Critical error.", exc_info=True)
        return None # Indicate critical failure
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading configuration {config_path}: {e}. Critical error.", exc_info=True)
        return None # Indicate critical failure

def discover_services(workflow_data: dict):
    """Discovers services and updates workflow_data."""
    logger.info("Starting service discovery...")
    config = workflow_data.get("config", {})
    if config is None: # Should not happen if load_config handles None return properly
        logger.error("Configuration is missing. Cannot proceed with service discovery.")
        workflow_data["discover_services_error"] = "Configuration missing"
        return

    try:
        kube_config_settings = config.get("kubernetes", {})
        namespace = kube_config_settings.get("default_namespace", "default")

        logger.info(f"Using namespace from config: '{namespace}' for service discovery.")
        # The actual call to the imported discover_k8s_services
        # This function now returns a list of dictionaries.
        retrieved_services = discover_k8s_services(namespace=namespace)

        workflow_data["discovered_endpoints"] = retrieved_services # Store the rich data

        if retrieved_services:
            logger.info(f"Successfully discovered {len(retrieved_services)} services.")
            for i, service_info in enumerate(retrieved_services):
                logger.info(f"  Service #{i+1}:")
                logger.info(f"    Name:         {service_info.get('name', 'N/A')}")
                logger.info(f"    Namespace:    {service_info.get('namespace', 'N/A')}")
                logger.info(f"    Type:         {service_info.get('service_type', 'N/A')}")
                logger.info(f"    Cluster IP:   {service_info.get('cluster_ip', 'N/A')}")

                ports = service_info.get('ports', [])
                logger.info(f"    Ports ({len(ports)}):")
                if ports:
                    for p in ports:
                        logger.info(f"      - Port Name: {p.get('name', 'N/A')}, Port: {p.get('port')}, Protocol: {p.get('protocol')}, Target: {p.get('target_port', 'N/A')}")
                else:
                    logger.info("      - No ports defined.")

                labels = service_info.get('labels', {})
                logger.info(f"    Labels ({len(labels)}): {'Yes' if labels else 'No'}")
                if labels: # Optional: log specific labels if needed, e.g., at DEBUG level
                    for k,v in labels.items(): logger.debug(f"      - Label: {k}={v}")

                annotations = service_info.get('annotations', {})
                logger.info(f"    Annotations ({len(annotations)}): {'Yes' if annotations else 'No'}")
                if annotations: # Optional: log specific annotations if needed, e.g., at DEBUG level
                     for k,v in annotations.items(): logger.debug(f"      - Annotation: {k}={v}")

                api_docs = service_info.get('api_doc_urls', [])
                logger.info(f"    API Doc URLs ({len(api_docs)}):")
                if api_docs:
                    for url in api_docs:
                        logger.info(f"      - {url}")
                else:
                    logger.info("      - No API docs found by probing or probing skipped.")
        else:
            logger.info("No service endpoints discovered or an error occurred during the k8s call.")

        logger.info("Service discovery completed.")
    except Exception as e:
        logger.error(f"Error during service discovery orchestration: {e}", exc_info=True)
        workflow_data["discovered_endpoints"] = [] # Ensure it's an empty list on error
        workflow_data["discover_services_error"] = str(e)


from test_generator.generator import generate_tests_from_api_spec

def generate_tests(workflow_data: dict):
    """Generates tests based on config and updates workflow_data."""
    logger.info("Starting test generation...")
    config = workflow_data.get("config", {})
    if config is None:
        logger.error("Configuration is missing. Cannot proceed with test generation.")
        workflow_data["generate_tests_error"] = "Configuration missing"
        return

    try:
        test_gen_config_settings = config.get("test_generation", {})
        api_spec_path = test_gen_config_settings.get("api_spec_path", "specs/default_api_spec.yaml")

        logger.info(f"Using API spec path from config: '{api_spec_path}' for test generation.")
        generated_api_tests = generate_tests_from_api_spec(api_spec_path)

        if generated_api_tests:
            logger.info(f"Generated {len(generated_api_tests)} API tests.")
            for test in generated_api_tests:
                logger.debug(f"  - Test: {test.get('test_name', 'Unnamed')}") # Changed to debug
        else:
            logger.info("No API tests were generated.")
        workflow_data["generated_tests"] = generated_api_tests
        logger.info("Test generation completed.")
    except Exception as e:
        logger.error(f"Error during test generation: {e}", exc_info=True)
        workflow_data["generated_tests"] = []
        workflow_data["generate_tests_error"] = str(e)


from execution_engine.executor import run_tests as run_execution_engine_tests

def execute_tests(workflow_data: dict):
    """Executes tests defined in workflow_data and updates it with results."""
    logger.info("Starting test execution...")
    test_definitions = workflow_data.get("generated_tests", [])

    if not test_definitions:
        logger.warning("No test definitions received from generation stage. Skipping execution.")
        workflow_data["execution_results"] = {"summary": "No tests to execute as generation produced no tests or failed."}
        # No error flag here, as it's a consequence of a previous stage's state
        return

    try:
        # TODO: kubeconfig_path should be configurable from workflow_data['config']
        logger.info(f"Executing {len(test_definitions)} tests...")
        run_execution_engine_tests(test_definitions, kubeconfig_path=None) # This function currently only prints

        logger.info("Execution engine finished processing tests. Storing mock results.")
        mock_results = {
            "test_run_id": "mock_run_001",
            "total_tests_executed": len(test_definitions),
            "passed": len(test_definitions),
            "failed": 0,
            "duration_seconds": 60.5,
            "metrics_summary": {"avg_latency_ms": 150, "error_rate": 0.0}
        }
        workflow_data["execution_results"] = mock_results
        logger.info("Test execution completed (mock results stored).")
    except Exception as e:
        logger.error(f"Error during test execution: {e}", exc_info=True)
        workflow_data["execution_results"] = {"summary": f"Test execution failed: {e}"}
        workflow_data["execute_tests_error"] = str(e)


from data_analyzer.analyzer import analyze_test_results as analyze_data_analyzer_results

def analyze_results(workflow_data: dict):
    """Analyzes execution results from workflow_data and updates it with a summary."""
    logger.info("Starting results analysis...")
    execution_results = workflow_data.get("execution_results", {})

    if not execution_results or "total_tests_executed" not in execution_results: # Check for valid results structure
        logger.warning("No valid execution results found or tests were skipped. Skipping analysis.")
        workflow_data["analysis_summary"] = {"summary": "No valid results to analyze.", "details": None}
        return

    try:
        analysis_summary_result = analyze_data_analyzer_results(execution_results) # Renamed to avoid conflict

        if analysis_summary_result:
            logger.info("Data analysis summary generated.")
            for key, value in analysis_summary_result.items():
                logger.debug(f"  - Analysis - {key}: {value}") # Changed to debug
        else:
            logger.warning("Analysis did not return a summary.")
        workflow_data["analysis_summary"] = analysis_summary_result
        logger.info("Results analysis completed.")
    except Exception as e:
        logger.error(f"Error during results analysis: {e}", exc_info=True)
        workflow_data["analysis_summary"] = {"summary": f"Analysis failed: {e}"}
        workflow_data["analyze_results_error"] = str(e)

from chaos_integrator.chaos_injector import inject_chaos_experiment

def trigger_chaos_tests(workflow_data: dict):
    """Triggers chaos tests and updates workflow_data with status."""
    logger.info("Starting chaos testing...")
    # config = workflow_data.get("config", {})

    mock_chaos_experiment_suite = [
        {"name": "Critical API Pod Resilience Test", "actions": [{"type": "PodChaos", "params": {"action": "pod-kill", "namespace": "production", "selector": {"app": "critical-api"}, "count": 1}}]},
        {"name": "Database Latency Injection", "actions": [{"type": "NetworkChaos", "params": {"action": "latency", "namespace": "production", "selector": {"app": "database"}, "latency_ms": 200, "duration_sec": 60}}]}
    ]

    all_experiments_successful = True
    try:
        for i, experiment_def in enumerate(mock_chaos_experiment_suite):
            exp_name = experiment_def.get('name', f'Unnamed Experiment {i+1}')
            logger.info(f"--- Starting Chaos Experiment: {exp_name} ---")
            # TODO: kubeconfig_path from workflow_data['config']
            success = inject_chaos_experiment(experiment_def, kubeconfig_path=None)
            if not success:
                all_experiments_successful = False
                logger.warning(f"Chaos experiment '{exp_name}' failed or was not fully injected.")
            else:
                logger.info(f"Chaos experiment '{exp_name}' simulated successfully.")
            logger.info(f"--- Finished Chaos Experiment: {exp_name} ---")

        if all_experiments_successful:
            logger.info("All mock chaos experiments were simulated successfully.")
            workflow_data["chaos_injection_status"] = True
        else:
            logger.warning("Some mock chaos experiments encountered issues.")
            workflow_data["chaos_injection_status"] = False
        logger.info("Chaos testing phase completed.")
    except Exception as e:
        logger.error(f"Error during chaos testing phase: {e}", exc_info=True)
        workflow_data["chaos_injection_status"] = False # Explicitly set to False on error
        workflow_data["trigger_chaos_error"] = str(e)


from report_hub.reporter import generate_performance_report as generate_rh_performance_report

def generate_report(workflow_data: dict):
    """Generates a report using data from workflow_data."""
    logger.info("Starting report generation...")

    analysis_summary_data = workflow_data.get("analysis_summary", {"summary": "Analysis data not available.", "issues_found": "N/A"})
    service_info_data = workflow_data.get("discovered_endpoints", [])
    chaos_status_data = workflow_data.get("chaos_injection_status")

    if not service_info_data:
        logger.warning("No service information available for reporting. Report might be incomplete.")
    if analysis_summary_data.get("summary") == "Analysis data not available.":
         logger.warning("No analysis summary available for reporting. Report might be incomplete.")

    try:
        report_message = generate_rh_performance_report(
            analysis_summary=analysis_summary_data,
            service_info=service_info_data,
            chaos_injection_status=chaos_status_data
        )
        logger.info(f"Report Hub status: {report_message}")
        workflow_data["report_message"] = report_message
        logger.info("Report generation completed.")
    except Exception as e:
        logger.error(f"Error during report generation: {e}", exc_info=True)
        workflow_data["report_message"] = f"Report generation failed: {e}"
        workflow_data["generate_report_error"] = str(e)


def main():
    """Main function to orchestrate the workflows."""
    # Basic logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout) # Ensure logs go to stdout
        ]
    )
    logger.info("Orchestrator starting...")
    parser = argparse.ArgumentParser(description="Chaos Engineering Orchestrator")
    parser.add_argument(
        "--config",
        default="orchestrator/config.yaml",
        help="Path to the YAML configuration file. Defaults to orchestrator/config.yaml"
    )

    # Add flags for controlling workflow stages
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Run only the service discovery stage."
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Run service discovery and test generation stages."
    )
    parser.add_argument(
        "--execute-only",
        action="store_true",
        help="Run discovery, generation, and test execution stages."
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Run up to the results analysis stage."
    )
    parser.add_argument(
        "--chaos-only",
        action="store_true",
        help="Run up to the chaos testing stage (includes discovery, generation, execution, analysis)."
    )
    # Default behavior (no flags or an explicit --full-cycle flag) will be the full pipeline.
    parser.add_argument(
        "--full-cycle",
        action="store_true",
        help="Run the full pipeline: discovery, generation, execution, analysis, chaos testing, and reporting. (Default if no other stage flag is provided)"
    )

    args = parser.parse_args()

    # Determine which stages to run
    run_discovery = True # Always run discovery if any later stage is requested or if it's discover_only
    run_generation = args.generate_only or args.execute_only or args.analyze_only or args.chaos_only or args.full_cycle
    run_execution = args.execute_only or args.analyze_only or args.chaos_only or args.full_cycle
    run_analysis = args.analyze_only or args.chaos_only or args.full_cycle
    run_chaos = args.chaos_only or args.full_cycle
    run_report = args.full_cycle

    # If no specific stage flag is provided, default to full_cycle
    if not (args.discover_only or args.generate_only or args.execute_only or args.analyze_only or args.chaos_only or args.full_cycle):
        print("No specific stage flag provided, defaulting to --full-cycle.")
        run_generation = run_execution = run_analysis = run_chaos = run_report = True


    print("Workflow stages to be executed:")
    print(f"  - Discovery: {run_discovery}")
    print(f"  - Generation: {run_generation}")
    print(f"  - Execution: {run_execution}")
    print(f"  - Analysis: {run_analysis}")
    print(f"  - Chaos: {run_chaos}")
    print(f"  - Report: {run_report}")




    # Initialize workflow_data dictionary
    workflow_data = {
        "config": {}, "discover_services_error": None,
        "discovered_endpoints": [], "generate_tests_error": None,
        "generated_tests": [], "execute_tests_error": None,
        "execution_results": {}, "analyze_results_error": None,
        "analysis_summary": {}, "trigger_chaos_error": None,
        "chaos_injection_status": None, "generate_report_error": None,
        "report_message": ""
    }

    # Load configuration early and store in workflow_data
    loaded_config = load_config(args.config)
    if loaded_config is None: # Critical error during load_config
        logger.critical("Failed to load configuration. Orchestrator cannot continue.")
        sys.exit(1)
    workflow_data["config"] = loaded_config

    # Log CLI flags used
    if args.discover_only: logger.info("CLI Flag: --discover-only specified.")
    if args.generate_only: logger.info("CLI Flag: --generate-only specified.")
    if args.execute_only: logger.info("CLI Flag: --execute-only specified.")
    if args.analyze_only: logger.info("CLI Flag: --analyze-only specified.")
    if args.chaos_only: logger.info("CLI Flag: --chaos-only specified.")
    if args.full_cycle or not any([args.discover_only, args.generate_only, args.execute_only, args.analyze_only, args.chaos_only]):
        logger.info("Running full cycle (either --full-cycle or default).")


    if run_discovery:
        logger.info("\n--- STAGE: Service Discovery ---")
        discover_services(workflow_data)
        if workflow_data.get("discover_services_error"):
            logger.critical(f"Critical error in Service Discovery: {workflow_data['discover_services_error']}. Exiting.")
            sys.exit(1)
        if args.discover_only:
            logger.info("Stopping after service discovery due to --discover-only flag.")
            # print(f"Final workflow_data: {workflow_data}") # For debugging
            sys.exit(0)

    if run_generation:
        logger.info("\n--- STAGE: Test Generation ---")
        generate_tests(workflow_data)
        if workflow_data.get("generate_tests_error"):
            logger.error(f"Error in Test Generation: {workflow_data['generate_tests_error']}. Subsequent stages might be affected.")
            # Decide if this is critical enough to exit, for now, let it continue if possible
        if args.generate_only:
            logger.info("Stopping after test generation due to --generate-only flag.")
            # print(f"Final workflow_data: {workflow_data}") # For debugging
            sys.exit(0)

    if run_execution:
        logger.info("\n--- STAGE: Test Execution ---")
        if workflow_data.get("generate_tests_error") or not workflow_data.get("generated_tests"):
            logger.warning("Skipping Test Execution because test generation failed or produced no tests.")
            workflow_data["execution_results"] = {"summary": "Skipped due to test generation issues."}
        else:
            execute_tests(workflow_data)

        if workflow_data.get("execute_tests_error"):
             logger.error(f"Error in Test Execution: {workflow_data['execute_tests_error']}. Subsequent stages might be affected.")

        if args.execute_only:
            logger.info("Stopping after test execution due to --execute-only flag.")
            # print(f"Final workflow_data: {workflow_data}") # For debugging
            sys.exit(0)

    if run_analysis:
        logger.info("\n--- STAGE: Results Analysis ---")
        if workflow_data.get("execute_tests_error") or not workflow_data.get("execution_results").get("total_tests_executed"):
            logger.warning("Skipping Results Analysis because test execution failed or produced no valid results.")
            workflow_data["analysis_summary"] = {"summary": "Skipped due to test execution issues."}
        else:
            analyze_results(workflow_data)

        if workflow_data.get("analyze_results_error"):
            logger.error(f"Error in Results Analysis: {workflow_data['analyze_results_error']}. Subsequent stages might be affected.")

        if args.analyze_only:
            logger.info("Stopping after results analysis due to --analyze-only flag.")
            # print(f"Final workflow_data: {workflow_data}") # For debugging
            sys.exit(0)

    if run_chaos:
        logger.info("\n--- STAGE: Chaos Testing ---")
        # Potentially add checks here if chaos should run based on previous stage errors
        trigger_chaos_tests(workflow_data)
        chaos_status_msg = "Not Run/Skipped"
        if workflow_data.get("trigger_chaos_error"):
            chaos_status_msg = f"Failed ({workflow_data['trigger_chaos_error']})"
        elif workflow_data["chaos_injection_status"] is True:
            chaos_status_msg = "Success"
        elif workflow_data["chaos_injection_status"] is False:
            chaos_status_msg = "Partial/Failed"
        logger.info(f"Chaos injection overall status: {chaos_status_msg}")

        if args.chaos_only:
            logger.info("Stopping after chaos testing due to --chaos-only flag.")
            # print(f"Final workflow_data: {workflow_data}") # For debugging
            sys.exit(0)

    if run_report:
        logger.info("\n--- STAGE: Report Generation ---")
        generate_report(workflow_data)
        logger.info(f"Orchestrator: Final report status: {workflow_data.get('report_message', 'N/A')}")

    logger.info("Orchestration finished.")
    # print(f"Final workflow_data state: {workflow_data}") # Optional: print final state for debugging

    # Exit with error if any stage reported an error that wasn't critical enough to exit immediately
    final_error_stages = [key for key, value in workflow_data.items() if key.endswith("_error") and value is not None]
    if final_error_stages:
        logger.error(f"Orchestration completed with errors in stages: {', '.join(final_error_stages)}")
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
