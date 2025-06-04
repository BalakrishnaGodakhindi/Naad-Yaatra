from kubernetes import client, config

def discover_services(namespace="production"):
    """
    Discovers services in a specified Kubernetes namespace.

    Args:
        namespace (str): The Kubernetes namespace to search for services.

    Returns:
        list: A list of tuples, where each tuple contains (service_name, service_port).
              Returns an empty list if an error occurs or no services are found.
    """
    endpoints = []
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
                return endpoints

        v1 = client.CoreV1Api()
        print(f"Attempting to list services in namespace: {namespace}")
        service_list = v1.list_namespaced_service(namespace)

        if not service_list.items:
            print(f"No services found in namespace '{namespace}'.")
            return endpoints

        for service in service_list.items:
            service_name = service.metadata.name
            # Assuming the first port is the primary one, or that there's at least one.
            if service.spec.ports:
                service_port = service.spec.ports[0].port
                endpoints.append((service_name, service_port))
                print(f"Discovered service: {service_name} on port {service_port}")
            else:
                print(f"Service {service_name} has no ports defined, skipping.")

        return endpoints

    except client.ApiException as e:
        if e.status == 404:
            print(f"Error: Namespace '{namespace}' not found.")
        else:
            print(f"Kubernetes API error: {e}")
        return endpoints
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return endpoints

if __name__ == '__main__':
    # Example usage for testing the module directly
    print("Attempting to discover services (stand-alone test)...")
    # You might want to change the default namespace for direct testing
    # For example, use 'default' if 'production' is not available in your test env
    discovered_endpoints = discover_services(namespace="default")
    if discovered_endpoints:
        print("\nDiscovered Endpoints (service_name, service_port):")
        for endpoint in discovered_endpoints:
            print(endpoint)
    else:
        print("No endpoints discovered or an error occurred.")
