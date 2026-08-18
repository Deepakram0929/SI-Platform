import streamlit as st
from kubernetes import client, config
import tempfile
import os
import io
import zipfile
from datetime import datetime


# ============================================================
# KUBECONFIG
# ============================================================

def load_kubeconfig(uploaded_file):

    kubeconfig_content = uploaded_file.getvalue()

    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        suffix=".yaml"
    ) as tmp:

        tmp.write(kubeconfig_content)
        kubeconfig_path = tmp.name

    try:
        config.load_kube_config(
            config_file=kubeconfig_path
        )

        return client.ApiClient()

    finally:
        try:
            os.unlink(kubeconfig_path)
        except Exception:
            pass


# ============================================================
# SAFE YAML
# ============================================================

def object_to_yaml(api_client, obj):

    return api_client.sanitize_for_serialization(obj)


def clean_metadata(obj):

    """
    Remove cluster-specific runtime metadata so the backup
    can be reused more safely.
    """

    if not isinstance(obj, dict):
        return obj

    metadata = obj.get("metadata", {})

    if isinstance(metadata, dict):

        for field in [
            "creationTimestamp",
            "resourceVersion",
            "uid",
            "managedFields",
            "generation",
            "selfLink",
        ]:

            metadata.pop(field, None)

    obj.pop("status", None)

    return obj


def yaml_dump(data):

    import yaml

    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
    )


# ============================================================
# BACKUP NAMESPACE
# ============================================================

def create_namespace_backup(
    api_client,
    namespace,
):

    apps_api = client.AppsV1Api(api_client)
    core_api = client.CoreV1Api(api_client)

    backup = {}

    # --------------------------------------------------------
    # NAMESPACE
    # --------------------------------------------------------

    ns_obj = core_api.read_namespace(
        namespace
    )

    backup["namespace.yaml"] = yaml_dump(
        clean_metadata(
            object_to_yaml(
                api_client,
                ns_obj
            )
        )
    )

    # --------------------------------------------------------
    # DEPLOYMENTS
    # --------------------------------------------------------

    deployments = (
        apps_api.list_namespaced_deployment(
            namespace
        )
    )

    deployment_images = []

    for deployment in deployments.items:

        name = deployment.metadata.name

        data = clean_metadata(
            object_to_yaml(
                api_client,
                deployment
            )
        )

        backup[
            f"deployments/{name}.yaml"
        ] = yaml_dump(data)

        containers = (
            deployment.spec.template.spec.containers
            or []
        )

        for container in containers:

            deployment_images.append(
                {
                    "deployment": name,
                    "container": container.name,
                    "image": container.image,
                }
            )

    # --------------------------------------------------------
    # DEPLOYMENT IMAGES
    # --------------------------------------------------------

    image_text = ""

    for item in deployment_images:

        image_text += (
            f"Deployment: {item['deployment']}\n"
            f"Container: {item['container']}\n"
            f"Image: {item['image']}\n"
            f"{'-' * 60}\n"
        )

    backup[
        "deployments/deployment-images.txt"
    ] = image_text

    # --------------------------------------------------------
    # STATEFULSETS
    # --------------------------------------------------------

    statefulsets = (
        apps_api.list_namespaced_stateful_set(
            namespace
        )
    )

    stateful_images = []

    for statefulset in statefulsets.items:

        name = statefulset.metadata.name

        data = clean_metadata(
            object_to_yaml(
                api_client,
                statefulset
            )
        )

        backup[
            f"statefulsets/{name}.yaml"
        ] = yaml_dump(data)

        containers = (
            statefulset
            .spec
            .template
            .spec
            .containers
            or []
        )

        for container in containers:

            stateful_images.append(
                {
                    "statefulset": name,
                    "container": container.name,
                    "image": container.image,
                }
            )

    # --------------------------------------------------------
    # STATEFULSET IMAGES
    # --------------------------------------------------------

    image_text = ""

    for item in stateful_images:

        image_text += (
            f"StatefulSet: {item['statefulset']}\n"
            f"Container: {item['container']}\n"
            f"Image: {item['image']}\n"
            f"{'-' * 60}\n"
        )

    backup[
        "statefulsets/statefulset-images.txt"
    ] = image_text

    # --------------------------------------------------------
    # CONFIGMAPS
    # --------------------------------------------------------

    configmaps = (
        core_api.list_namespaced_config_map(
            namespace
        )
    )

    for cm in configmaps.items:

        name = cm.metadata.name

        data = clean_metadata(
            object_to_yaml(
                api_client,
                cm
            )
        )

        backup[
            f"configmaps/{name}.yaml"
        ] = yaml_dump(data)

    # --------------------------------------------------------
    # SECRETS
    # --------------------------------------------------------

    secrets = (
        core_api.list_namespaced_secret(
            namespace
        )
    )

    for secret in secrets.items:

        name = secret.metadata.name

        data = clean_metadata(
            object_to_yaml(
                api_client,
                secret
            )
        )

        backup[
            f"secrets/{name}.yaml"
        ] = yaml_dump(data)

    # --------------------------------------------------------
    # PVC
    # --------------------------------------------------------

    pvcs = (
        core_api.list_namespaced_persistent_volume_claim(
            namespace
        )
    )

    pvc_names = []

    for pvc in pvcs.items:

        name = pvc.metadata.name

        pvc_names.append(name)

        data = clean_metadata(
            object_to_yaml(
                api_client,
                pvc
            )
        )

        backup[
            f"pvc/{name}.yaml"
        ] = yaml_dump(data)

    backup[
        "pvc/pvc-names.txt"
    ] = "\n".join(pvc_names)

    # --------------------------------------------------------
    # SERVICES + WORKLOAD IMAGES
    # --------------------------------------------------------

    services = (
        core_api.list_namespaced_service(
            namespace
        )
    )


    def selector_matches_pod(
        selector,
        pod_labels,
    ):

        if not selector:
            return False

        if not pod_labels:
            return False

        for key, value in selector.items():

            if pod_labels.get(key) != value:
                return False

        return True


    # Get all pods in namespace once
    pods = core_api.list_namespaced_pod(
        namespace
    )


    for service in services.items:

        service_name = service.metadata.name

        # ----------------------------------------------------
        # SERVICE YAML
        # ----------------------------------------------------

        service_data = clean_metadata(
            object_to_yaml(
                api_client,
                service
            )
        )

        backup[
            f"services/{service_name}/service.yaml"
        ] = yaml_dump(
            service_data
        )


        # ----------------------------------------------------
        # SERVICE SELECTOR
        # ----------------------------------------------------

        selector = (
            service.spec.selector
            or {}
        )


        image_lines = []

        image_lines.append(
            f"Service: {service_name}"
        )

        image_lines.append(
            ""
        )

        if selector:

            image_lines.append(
                "Selector:"
            )

            for key, value in selector.items():

                image_lines.append(
                    f"  {key}={value}"
                )

            image_lines.append("")


        # ----------------------------------------------------
        # FIND PODS BEHIND SERVICE
        # ----------------------------------------------------

        matched_pods = []

        for pod in pods.items:

            pod_labels = (
                pod.metadata.labels
                or {}
            )

            if selector_matches_pod(
                selector,
                pod_labels
            ):

                matched_pods.append(
                    pod
                )


        # ----------------------------------------------------
        # GET IMAGES
        # ----------------------------------------------------

        if not matched_pods:

            image_lines.append(
                "No matching pods found."
            )

        else:

            for pod in matched_pods:

                image_lines.append(
                    f"Pod: {pod.metadata.name}"
                )

                # --------------------------------------------
                # NORMAL CONTAINERS
                # --------------------------------------------

                for container in (
                    pod.spec.containers
                    or []
                ):

                    image_lines.append(
                        f"  Container: {container.name}"
                    )

                    image_lines.append(
                        f"  Image: {container.image}"
                    )

                    image_lines.append("")


                # --------------------------------------------
                # INIT CONTAINERS
                # --------------------------------------------

                for container in (
                    pod.spec.init_containers
                    or []
                ):

                    image_lines.append(
                        f"  Init Container: {container.name}"
                    )

                    image_lines.append(
                        f"  Image: {container.image}"
                    )

                    image_lines.append("")

                image_lines.append(
                    "-" * 70
                )


    # ----------------------------------------------------
    # SERVICE IMAGES FILE
    # ----------------------------------------------------

    backup[
        f"services/{service_name}/images.txt"
    ] = "\n".join(
        image_lines
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = f"""
SI-PLATFORM NAMESPACE BACKUP
============================

Namespace:
{namespace}

Backup Time:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Deployments:
{len(deployments.items)}

StatefulSets:
{len(statefulsets.items)}

ConfigMaps:
{len(configmaps.items)}

Secrets:
{len(secrets.items)}

PVCs:
{len(pvcs.items)}

Services:
{len(services.items)}
"""

    backup["BACKUP-SUMMARY.txt"] = summary

    return backup


# ============================================================
# CREATE ZIP
# ============================================================

def create_zip(backup):

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for filename, content in backup.items():

            zip_file.writestr(
                filename,
                content
            )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# PAGE
# ============================================================

def render_namespace_backup():

    st.markdown(
        """
        <style>

        .backup-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
        }

        .backup-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 25px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="backup-title">'
        '💾 Namespace Backup'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="backup-subtitle">'
        'Backup Kubernetes workloads and configuration '
        'resources namespace by namespace.'
        '</div>',
        unsafe_allow_html=True
    )

    # ========================================================
    # KUBECONFIG
    # ========================================================

    uploaded_file = st.file_uploader(
        "Upload kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf"
        ],
        key="namespace_backup_kubeconfig"
    )

    if uploaded_file is None:

        st.info(
            "Upload a kubeconfig file to continue."
        )

        return

    # ========================================================
    # CONNECT
    # ========================================================

    try:

        api_client = load_kubeconfig(
            uploaded_file
        )

        core_api = client.CoreV1Api(
            api_client
        )

        namespaces = (
            core_api.list_namespace()
        )

        namespace_names = sorted(
            [
                ns.metadata.name
                for ns in namespaces.items
            ]
        )

    except Exception as exc:

        st.error(
            f"Failed to connect to Kubernetes cluster: {exc}"
        )

        return

    # ========================================================
    # NAMESPACE
    # ========================================================

    selected_namespace = st.selectbox(
        "Select Namespace",
        namespace_names,
        key="backup_namespace"
    )

    st.divider()

    st.markdown(
        "### 📦 Backup Contents"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.info("Deployments\n\nYAML + Images")

    with c2:
        st.info("StatefulSets\n\nYAML + Images")

    with c3:
        st.info("ConfigMaps + Secrets")

    with c4:
        st.info("PVCs + Services")

    st.warning(
        "⚠️ Secret YAML files contain Kubernetes encoded "
        "Secret data. Store the generated backup securely."
    )

    # ========================================================
    # BACKUP
    # ========================================================

    if st.button(
        "💾 Create Namespace Backup",
        use_container_width=True,
        type="primary",
        key="create_namespace_backup"
    ):

        try:

            with st.spinner(
                f"Creating backup for "
                f"{selected_namespace}..."
            ):

                backup = create_namespace_backup(
                    api_client,
                    selected_namespace
                )

                zip_data = create_zip(
                    backup
                )

            st.success(
                f"Backup created successfully for "
                f"`{selected_namespace}`."
            )

            # ------------------------------------------------
            # SUMMARY
            # ------------------------------------------------

            st.markdown(
                "### 📋 Backup Files"
            )

            for filename in sorted(
                backup.keys()
            ):

                st.write(
                    f"📄 {filename}"
                )

            st.download_button(
                "⬇️ Download Namespace Backup ZIP",
                data=zip_data,
                file_name=(
                    f"{selected_namespace}-"
                    f"backup-"
                    f"{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    f".zip"
                ),
                mime="application/zip",
                use_container_width=True
            )

        except Exception as exc:

            st.error(
                f"Backup failed: {exc}"
            )