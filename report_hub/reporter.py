from typing import Dict, Any, List

def generate_performance_report(
    analysis_summary: Dict[str, Any],
    service_info: List[Dict[str, Any]],
    chaos_injection_status: bool = None # Optional: include status of chaos tests
    ) -> str:
    """
    Generates a performance report based on analysis summary and service information.

    This function will eventually format data into a comprehensive report and
    potentially send it to a reporting backend like Elasticsearch or trigger
    other actions (e.g., Kubeflow Pipeline for report generation).

    Args:
        analysis_summary (Dict[str, Any]): The summary dictionary from the Data Analyzer.
        service_info (List[Dict[str, Any]]): A list of dictionaries, where each dictionary
                                             contains information about a discovered service
                                             (e.g., name, port, version). For now, we expect
                                             tuples from discover_services.
        chaos_injection_status (bool, optional): Status of chaos injection, if performed.

    Returns:
        str: A message indicating the report generation status, possibly with a mock path.
    """
    print("Generating performance report...")

    if not analysis_summary:
        analysis_summary = {"summary": "No analysis data provided."}
    if not service_info:
        service_info = [{"name": "Unknown", "port": 0, "details": "No service data provided."}]

    print("\n--- Data Received for Reporting ---")
    print("Service Information:")
    if service_info and isinstance(service_info[0], tuple): # Adapt if discover_services returns list of tuples
        adapted_service_info = [{"name": item[0], "port": item[1]} for item in service_info]
        for service in adapted_service_info:
            print(f"  - Service: {service.get('name')}, Port: {service.get('port')}")
    else: # Assuming list of dicts
        for service in service_info:
            print(f"  - Service: {service.get('name')}, Port: {service.get('port')}, Details: {service.get('details', 'N/A')}")

    print("\nAnalysis Summary:")
    for key, value in analysis_summary.items():
        print(f"  - {key.replace('_', ' ').capitalize()}: {value}")

    if chaos_injection_status is not None:
        print(f"\nChaos Injection Status: {'Succeeded' if chaos_injection_status else 'Failed/Not run'}")

    # Placeholder for actual report generation (e.g., HTML, PDF, JSON output)
    # Placeholder for sending data to Elasticsearch or other systems
    # For example:
    # report_content = f"<html><body><h1>Performance Report</h1>...</body></html>"
    # with open("/tmp/performance_report.html", "w") as f:
    #     f.write(report_content)
    # es_client.index(index="performance-reports", document=full_report_data)

    mock_report_path = "/mnt/reports/performance_report_mock.html"
    report_status_message = f"Report generated successfully (mock). View at {mock_report_path}"

    print(f"\n{report_status_message}")
    return report_status_message

if __name__ == '__main__':
    # Example usage for testing the module directly
    print("Testing generate_performance_report function...")

    mock_services = [
        ("user-service", 8080),
        ("order-service", 8081),
        ("payment-service", 8082)
    ]

    mock_analysis = {
        "summary": "Overall system performance is stable under normal load.",
        "issues_found": 1,
        "bottlenecks_identified": ["payment-service checkout latency spike under 100rps"],
        "performance_regression_detected": False,
        "recommendations": "Investigate payment-service checkout process."
    }

    print("\n--- Generating Report (Standard) ---")
    status1 = generate_performance_report(mock_analysis, mock_services)
    print(f"Reporter main test output: {status1}")

    print("\n--- Generating Report (With Chaos Success) ---")
    status2 = generate_performance_report(mock_analysis, mock_services, chaos_injection_status=True)
    print(f"Reporter main test output: {status2}")

    print("\n--- Generating Report (With Chaos Failure) ---")
    status3 = generate_performance_report(mock_analysis, mock_services, chaos_injection_status=False)
    print(f"Reporter main test output: {status3}")

    print("\n--- Generating Report (Empty/Null Inputs) ---")
    status4 = generate_performance_report({}, [])
    print(f"Reporter main test output: {status4}")
