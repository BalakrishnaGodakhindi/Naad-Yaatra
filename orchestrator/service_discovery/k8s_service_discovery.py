from kubernetes import client, config
import requests # For making HTTP requests to probe for API docs
import logging # For logging

logger = logging.getLogger(__name__)

COMMON_API_DOC_PATHS = [
    "/openapi.json", "/swagger.json", "/api/swagger.json",
    "/openapi.yaml", "/swagger.yaml", "/api/swagger.yaml",
    "/v2/api-docs", "/v3/api-docs", "/api/v2/api-docs", "/api/v3/api-docs",
    "/api/docs", "/docs", "/apispec", "/apispec.json", "/apispec.yaml",
    # Add more based on common frameworks or conventions
]

def probe_service_for_api_docs(service_info: dict, timeout_seconds: int = 2) -> list[str]:
    """
    Probes a service on its HTTP/S ports for common API documentation paths.

    Args:
        service_info (dict): A dictionary containing service details (name, cluster_ip, ports).
        timeout_seconds (int): Timeout for each HTTP request.

    Returns:
        list[str]: A list of successfully probed API documentation URLs.
    """
    found_doc_urls = []
    cluster_ip = service_info.get("cluster_ip")
    service_name = service_info.get("name", "unknown-service")

    if not cluster_ip or cluster_ip == "None": # "None" can be a string value for ClusterIP if headless
        logger.debug(f"Service {service_name} has no ClusterIP or is headless; skipping API doc probing.")
        return found_doc_urls

    for port_info in service_info.get("ports", []):
        port = port_info.get("port")
        port_name = port_info.get("name", "").lower()
        protocol = port_info.get("protocol", "TCP").upper()

        # Probe only if it's a TCP port and likely HTTP/S
        if protocol != "TCP":
            logger.debug(f"Skipping non-TCP port {port}/{protocol} for service {service_name}")
            continue

        # Heuristic to identify HTTP/S ports
        is_http_port = (
            port in [80, 443, 8000, 8080, 8888] or
            "http" in port_name or
            "https" in port_name or
            "web" in port_name or
            "api" in port_name
        )

        if not is_http_port:
            logger.debug(f"Skipping port {port} (name: '{port_name}') for service {service_name} as it's not identified as HTTP/S.")
            continue

        # For now, primarily trying HTTP. HTTPS would require more robust cert handling.
        # If port is 443 or name suggests https, we could prioritize https, but keeping it simple for now.
        scheme = "http"
        # if port == 443 or "https" in port_name:
        # scheme = "https" # Consider this for future enhancement

        base_url = f"{scheme}://{cluster_ip}:{port}"
        logger.debug(f"Probing service {service_name} at base URL: {base_url}")

        for doc_path in COMMON_API_DOC_PATHS:
            probe_url = f"{base_url}{doc_path}"
            try:
                logger.debug(f"Attempting to GET {probe_url} for service {service_name}")
                response = requests.get(probe_url, timeout=timeout_seconds, allow_redirects=True)
                if response.status_code == 200:
                    # Further validation could be added here (e.g., check content-type)
                    logger.info(f"Successfully found API doc for service {service_name} at {probe_url} (status: {response.status_code})")
                    found_doc_urls.append(probe_url)
                else:
                    logger.debug(f"Failed to find API doc for service {service_name} at {probe_url} (status: {response.status_code})")
            except requests.exceptions.Timeout:
                logger.debug(f"Timeout while trying to GET {probe_url} for service {service_name}")
            except requests.exceptions.ConnectionError:
                logger.debug(f"Connection error while trying to GET {probe_url} for service {service_name}")
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception for service {service_name} at {probe_url}: {e}")
            except Exception as e: # Catch any other unexpected errors during probing a specific URL
                logger.error(f"Unexpected error probing {probe_url} for {service_name}: {e}", exc_info=False)


    return found_doc_urls


def discover_services(namespace="production"):
    """
    Discovers services in a specified Kubernetes namespace and attempts to find
    their API documentation URLs.

    Each service is represented as a dictionary with the following structure:
    {
        "name": str,               # Name of the service
        "namespace": str,          # Namespace of the service
        "ports": list[dict],       # List of port information dictionaries
                                   # Each port dict: {"name": str, "port": int, "protocol": str, "target_port": int | str}
                                   # Defaults to [] if no ports are defined.
        "labels": dict[str, str],  # Service labels, defaults to {}
        "annotations": dict[str, str], # Service annotations, defaults to {}
        "service_type": str,       # e.g., "ClusterIP", "NodePort", "LoadBalancer"
        "cluster_ip": str,         # Cluster IP address of the service (can be "None" for headless)
        "api_doc_urls": list[str]  # List of potential API documentation URLs found by probing.
                                   # Defaults to [] if none found or probing skipped.
    }
    (Note: This structure may be formalized into a Python data class in the future for
     stricter type checking and clearer contracts.)

    Args:
        namespace (str): The Kubernetes namespace to search for services.

    Returns:
        list[dict]: A list of dictionaries, each detailing a discovered service.
                    Returns an empty list if an error occurs or no services are found.
    """
    discovered_services_list = []
    try:
        # Try loading in-cluster configuration
        try:
            config.load_incluster_config()
            print("Using in-cluster Kubernetes configuration.")
        except config.ConfigException:
            # Fallback to kubeconfig if in-cluster fails
            try:
                config.load_kube_config()
                print("Using local kubeconfig for Kubernetes configuration.")
            except config.ConfigException as e:
                print(f"Could not load Kubernetes configuration: {e}")
                return discovered_services_list

        core_v1_api = client.CoreV1Api()
        logger.info(f"Attempting to list services in namespace: {namespace}")
        service_list_response = core_v1_api.list_namespaced_service(namespace, watch=False)

        if not service_list_response.items:
            logger.info(f"No services found in namespace '{namespace}'.")
            return discovered_services_list

        for service in service_list_response.items:
            service_data = {
                "name": service.metadata.name,
                "namespace": service.metadata.namespace,
                "ports": [{"name": p.name, "port": p.port, "protocol": str(p.protocol).upper(), "target_port": p.target_port} for p in service.spec.ports] if service.spec.ports else [],
                "labels": service.metadata.labels if service.metadata.labels is not None else {},
                "annotations": service.metadata.annotations if service.metadata.annotations is not None else {},
                "service_type": str(service.spec.type),
                "cluster_ip": service.spec.cluster_ip if service.spec.cluster_ip else "None", # Ensure "None" string if NoneType
                "api_doc_urls": []
            }

            logger.info(f"Discovered service: {service_data['name']} (Type: {service_data['service_type']}, ClusterIP: {service_data['cluster_ip']})")
            for port_info in service_data['ports']:
                logger.debug(f"  Port: {port_info['port']}/{port_info['protocol']} (Name: {port_info.get('name', 'N/A')}, Target: {port_info.get('target_port', 'N/A')})")

            # Probe for API docs if ClusterIP is available
            if service_data["cluster_ip"] and service_data["cluster_ip"] != "None":
                logger.debug(f"Probing for API docs for service: {service_data['name']}")
                service_data["api_doc_urls"] = probe_service_for_api_docs(service_data)
                if service_data["api_doc_urls"]:
                    logger.info(f"Found {len(service_data['api_doc_urls'])} potential API doc URL(s) for {service_data['name']}: {service_data['api_doc_urls']}")
                else:
                    logger.debug(f"No API doc URLs found for {service_data['name']} after probing.")
            else:
                logger.debug(f"Skipping API doc probing for service {service_data['name']} due to missing or 'None' ClusterIP.")

            discovered_services_list.append(service_data)

        return discovered_services_list

    except client.ApiException as e:
        if e.status == 404:
            logger.error(f"Namespace '{namespace}' not found.")
        else:
            logger.error(f"Kubernetes API error while listing services: {e}", exc_info=True)
        return discovered_services_list
    except Exception as e:
        logger.error(f"An unexpected error occurred during service discovery: {e}", exc_info=True)
        return discovered_services_list

if __name__ == '__main__':
    # Basic logging setup for standalone execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Attempting to discover services (stand-alone test)...")
    # Ensure KUBECONFIG is set up if running outside a cluster, or rely on in-cluster config.
    # Using "default" namespace for testing.
    services_discovered = discover_services(namespace="default") # Renamed variable

    if services_discovered:
        logger.info(f"\n--- Discovered Services ({len(services_discovered)} total) ---")
        for i, service_details in enumerate(services_discovered):
            logger.info(f"\nService #{i+1}:")
            logger.info(f"  Name:         {service_details.get('name', 'N/A')}")
            logger.info(f"  Namespace:    {service_details.get('namespace', 'N/A')}")
            logger.info(f"  Service Type: {service_details.get('service_type', 'N/A')}")
            logger.info(f"  Cluster IP:   {service_details.get('cluster_ip', 'N/A')}")

            ports = service_details.get('ports', [])
            logger.info(f"  Ports ({len(ports)}):")
            if ports:
                for p in ports:
                    logger.info(f"    - Port Name: {p.get('name', 'N/A')}, Port: {p.get('port')}, Protocol: {p.get('protocol')}, Target Port: {p.get('target_port', 'N/A')}")
            else:
                logger.info("    - None")

            labels = service_details.get('labels', {})
            logger.info(f"  Labels ({len(labels)}):")
            if labels:
                for k, v in labels.items():
                    logger.info(f"    - {k}: {v}")
            else:
                logger.info("    - None")

            annotations = service_details.get('annotations', {})
            logger.info(f"  Annotations ({len(annotations)}):")
            if annotations:
                for k, v in annotations.items():
                    logger.info(f"    - {k}: {v}")
            else:
                logger.info("    - None")

            api_docs = service_details.get('api_doc_urls', [])
            logger.info(f"  API Doc URLs ({len(api_docs)}):")
            if api_docs:
                for url in api_docs:
                    logger.info(f"    - {url}")
            else:
                logger.info("    - None found or probing skipped.")
    else:
        logger.info("No services discovered or an error occurred.")
