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

        image_lines.append("")

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
        ] = "\n".join(image_lines)

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
# NAMESPACE SELECTION CALLBACKS
# ============================================================

def select_all_backup_namespaces(namespace_names):

    """
    Select all namespaces.

    This callback runs before Streamlit reruns the page,
    so modifying the widget state here is safe.
    """

    st.session_state[
        "backup_namespace_selector"
    ] = list(namespace_names)


def clear_backup_namespaces():

    """
    Clear namespace selection.

    This callback runs before Streamlit reruns the page,
    so modifying the widget state here is safe.
    """

    st.session_state[
        "backup_namespace_selector"
    ] = []


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

    if not namespace_names:

        st.warning(
            "No namespaces found in the Kubernetes cluster."
        )

        return

    # ========================================================
    # NAMESPACE SCOPE
    # ========================================================

    st.markdown(
        "### Select scope"
    )

    scope = st.radio(
        "Select scope",
        [
            "Selected Namespace",
            "All Namespaces"
        ],
        horizontal=True,
        key="backup_namespace_scope",
        label_visibility="collapsed"
    )

    # ========================================================
    # NAMESPACE SESSION STATE
    # ========================================================

    if (
        "backup_namespace_selector"
        not in st.session_state
    ):

        st.session_state[
            "backup_namespace_selector"
        ] = []

    # Remove namespaces that no longer exist
    # in the currently connected cluster.

    valid_selection = [
        ns
        for ns in st.session_state[
            "backup_namespace_selector"
        ]
        if ns in namespace_names
    ]

    if (
        valid_selection
        != st.session_state[
            "backup_namespace_selector"
        ]
    ):

        st.session_state[
            "backup_namespace_selector"
        ] = valid_selection

    # ========================================================
    # SELECTED NAMESPACE MODE
    # ========================================================

    if scope == "Selected Namespace":

        st.markdown(
            "**Select Namespace(s)**"
        )

        selected_namespaces = st.multiselect(
            "Select Namespace(s)",
            options=namespace_names,
            key="backup_namespace_selector",
            placeholder="Select one or more namespaces...",
            label_visibility="collapsed"
        )

        c1, c2 = st.columns(2)

        # ----------------------------------------------------
        # SELECT ALL
        # ----------------------------------------------------

        with c1:

            st.button(
                "Select All Listed Namespaces",
                use_container_width=True,
                key="select_all_backup_namespaces",
                on_click=select_all_backup_namespaces,
                args=(namespace_names,)
            )

        # ----------------------------------------------------
        # CLEAR
        # ----------------------------------------------------

        with c2:

            st.button(
                "Clear Namespace Selection",
                use_container_width=True,
                key="clear_backup_namespaces",
                on_click=clear_backup_namespaces
            )

    # ========================================================
    # ALL NAMESPACES MODE
    # ========================================================

    else:

        selected_namespaces = list(
            namespace_names
        )

        st.success(
            f"All namespaces selected "
            f"({len(selected_namespaces)})."
        )

    st.divider()

    # ========================================================
    # BACKUP CONTENTS
    # ========================================================

    st.markdown(
        "### 📦 Backup Contents"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.info(
            "Deployments\n\nYAML + Images"
        )

    with c2:

        st.info(
            "StatefulSets\n\nYAML + Images"
        )

    with c3:

        st.info(
            "ConfigMaps + Secrets"
        )

    with c4:

        st.info(
            "PVCs + Services"
        )

    st.warning(
        "⚠️ Secret YAML files contain Kubernetes encoded "
        "Secret data. Store the generated backup securely."
    )

    # ========================================================
    # SELECTION STATUS
    # ========================================================

    if selected_namespaces:

        if len(selected_namespaces) == 1:

            st.caption(
                f"1 namespace selected: "
                f"`{selected_namespaces[0]}`"
            )

        else:

            st.caption(
                f"{len(selected_namespaces)} "
                f"namespaces selected."
            )

    else:

        st.info(
            "Select at least one namespace "
            "to create a backup."
        )

    # ========================================================
    # BACKUP BUTTON
    # ========================================================

    if st.button(
        "💾 Create Namespace Backup",
        use_container_width=True,
        type="primary",
        key="create_namespace_backup"
    ):

        if not selected_namespaces:

            st.error(
                "Please select at least one namespace."
            )

            return

        combined_backup = {}

        successful_namespaces = []

        failed_namespaces = []

        # ====================================================
        # PROGRESS
        # ====================================================

        progress = st.progress(
            0,
            text="Preparing namespace backup..."
        )

        total = len(
            selected_namespaces
        )

        # ====================================================
        # BACKUP EACH NAMESPACE
        # ====================================================

        for index, namespace in enumerate(
            selected_namespaces,
            start=1
        ):

            try:

                progress.progress(
                    (index - 1) / total,
                    text=(
                        f"Creating backup for namespace "
                        f"{namespace} "
                        f"({index}/{total})..."
                    )
                )

                backup = create_namespace_backup(
                    api_client,
                    namespace
                )

                # --------------------------------------------
                # Put each namespace under its own directory.
                # --------------------------------------------

                for filename, content in backup.items():

                    combined_backup[
                        f"{namespace}/{filename}"
                    ] = content

                successful_namespaces.append(
                    namespace
                )

            except Exception as exc:

                failed_namespaces.append(
                    (
                        namespace,
                        str(exc)
                    )
                )

        # ====================================================
        # COMBINED SUMMARY
        # ====================================================

        combined_summary = f"""
SI-PLATFORM NAMESPACE BACKUP
============================

Backup Time:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Requested Namespaces:
{len(selected_namespaces)}

Successful Namespaces:
{len(successful_namespaces)}

Failed Namespaces:
{len(failed_namespaces)}

Successful:
{
    chr(10).join(successful_namespaces)
    if successful_namespaces
    else "None"
}

Failed:
{
    chr(10).join(
        f"{namespace}: {error}"
        for namespace, error in failed_namespaces
    )
    if failed_namespaces
    else "None"
}
"""

        combined_backup[
            "BACKUP-SUMMARY.txt"
        ] = combined_summary

        progress.progress(
            1.0,
            text="Backup completed."
        )

        # ====================================================
        # RESULTS
        # ====================================================

        if successful_namespaces:

            st.success(
                f"Backup created successfully for "
                f"{len(successful_namespaces)} "
                f"namespace(s)."
            )

        if failed_namespaces:

            st.error(
                f"{len(failed_namespaces)} "
                f"namespace(s) failed."
            )

            for namespace, error in failed_namespaces:

                st.warning(
                    f"`{namespace}`: {error}"
                )

        if not combined_backup:

            st.error(
                "No backup data was generated."
            )

            return

        # ====================================================
        # CREATE ZIP
        # ====================================================

        zip_data = create_zip(
            combined_backup
        )

        # ====================================================
        # BACKUP FILES
        # ====================================================

        st.markdown(
            "### 📋 Backup Files"
        )

        for filename in sorted(
            combined_backup.keys()
        ):

            st.write(
                f"📄 {filename}"
            )

        # ====================================================
        # DOWNLOAD NAME
        # ====================================================

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        if len(successful_namespaces) == 1:

            backup_name = (
                f"{successful_namespaces[0]}-"
                f"backup-"
                f"{timestamp}.zip"
            )

        else:

            backup_name = (
                f"namespaces-backup-"
                f"{timestamp}.zip"
            )

        # ====================================================
        # DOWNLOAD
        # ====================================================

        st.download_button(
            "⬇️ Download Namespace Backup ZIP",
            data=zip_data,
            file_name=backup_name,
            mime="application/zip",
            use_container_width=True,
            key="download_namespace_backup"
        )