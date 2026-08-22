import base64
import io
import zipfile
import re

import pandas as pd
import streamlit as st
import yaml

from kubernetes import client
from kubernetes import config


# ============================================================
# MONGODB URL PATTERN
# ============================================================

MONGO_PATTERN = re.compile(
    r"mongodb(?:\+srv)?://[^\s'\"<>]+",
    re.IGNORECASE,
)


# ============================================================
# KUBERNETES CLIENT
# ============================================================

def create_kubernetes_client(kubeconfig_bytes):

    kubeconfig_text = kubeconfig_bytes.decode(
        "utf-8",
        errors="ignore",
    )

    kubeconfig_dict = yaml.safe_load(
        kubeconfig_text
    )

    if not isinstance(kubeconfig_dict, dict):
        raise ValueError(
            "Invalid kubeconfig format."
        )

    configuration = client.Configuration()

    config.load_kube_config_from_dict(
        kubeconfig_dict,
        client_configuration=configuration,
    )

    return client.ApiClient(
        configuration=configuration
    )


# ============================================================
# EXTRACT MONGODB STRINGS
# ============================================================

def extract_mongodb_strings(text):

    if not text:
        return []

    matches = MONGO_PATTERN.findall(
        str(text)
    )

    results = []

    for value in matches:

        value = value.rstrip(
            ".,;)}]}>"
        )

        if value not in results:
            results.append(value)

    return results


# ============================================================
# ADD RESULT
# ============================================================

def add_result(
    results,
    namespace,
    resource_type,
    resource_name,
    key,
    db_string,
):

    results.append(
        {
            "Namespace": namespace,
            "Resource Type": resource_type,
            "Resource Name": resource_name,
            "Key": key,
            "DB String": db_string,
        }
    )


# ============================================================
# SCAN SECRET
# ============================================================

def scan_secrets(
    core_api,
    namespace,
):

    results = []

    try:

        response = core_api.list_namespaced_secret(
            namespace
        )

        for secret in response.items:

            if not secret.data:
                continue

            for key, encoded_value in secret.data.items():

                try:

                    decoded_value = (
                        base64.b64decode(
                            encoded_value
                        )
                        .decode(
                            "utf-8",
                            errors="ignore",
                        )
                    )

                except Exception:

                    continue

                mongo_strings = (
                    extract_mongodb_strings(
                        decoded_value
                    )
                )

                for mongo in mongo_strings:

                    add_result(
                        results,
                        namespace,
                        "Secret",
                        secret.metadata.name,
                        key,
                        mongo,
                    )

    except Exception:
        pass

    return results


# ============================================================
# SCAN CONFIGMAP
# ============================================================

def scan_configmaps(
    core_api,
    namespace,
):

    results = []

    try:

        response = (
            core_api.list_namespaced_config_map(
                namespace
            )
        )

        for configmap in response.items:

            if not configmap.data:
                continue

            for key, value in configmap.data.items():

                mongo_strings = (
                    extract_mongodb_strings(
                        value
                    )
                )

                for mongo in mongo_strings:

                    add_result(
                        results,
                        namespace,
                        "ConfigMap",
                        configmap.metadata.name,
                        key,
                        mongo,
                    )

    except Exception:
        pass

    return results


# ============================================================
# GET WORKLOAD CONTAINERS
# ============================================================

def get_containers(
    resource,
):

    try:

        return resource.spec.template.spec.containers

    except Exception:

        return []


# ============================================================
# SCAN WORKLOAD CONTAINER
# ============================================================

def scan_container(
    results,
    namespace,
    resource_type,
    resource_name,
    container,
):

    # ========================================================
    # ENV VARIABLES
    # ========================================================

    if container.env:

        for env in container.env:

            # Direct value
            if env.value:

                mongo_strings = (
                    extract_mongodb_strings(
                        env.value
                    )
                )

                for mongo in mongo_strings:

                    add_result(
                        results,
                        namespace,
                        resource_type,
                        resource_name,
                        env.name,
                        mongo,
                    )

    # ========================================================
    # COMMAND
    # ========================================================

    if container.command:

        for index, command in enumerate(
            container.command
        ):

            mongo_strings = (
                extract_mongodb_strings(
                    command
                )
            )

            for mongo in mongo_strings:

                add_result(
                    results,
                    namespace,
                    resource_type,
                    resource_name,
                    f"command[{index}]",
                    mongo,
                )

    # ========================================================
    # ARGS
    # ========================================================

    if container.args:

        for index, argument in enumerate(
            container.args
        ):

            mongo_strings = (
                extract_mongodb_strings(
                    argument
                )
            )

            for mongo in mongo_strings:

                add_result(
                    results,
                    namespace,
                    resource_type,
                    resource_name,
                    f"args[{index}]",
                    mongo,
                )

    return results


# ============================================================
# SCAN DEPLOYMENTS
# ============================================================

def scan_deployments(
    apps_api,
    namespace,
):

    results = []

    try:

        response = (
            apps_api.list_namespaced_deployment(
                namespace
            )
        )

        for deployment in response.items:

            containers = get_containers(
                deployment
            )

            for container in containers:

                scan_container(
                    results,
                    namespace,
                    "Deployment",
                    deployment.metadata.name,
                    container,
                )

    except Exception:
        pass

    return results


# ============================================================
# SCAN STATEFULSETS
# ============================================================

def scan_statefulsets(
    apps_api,
    namespace,
):

    results = []

    try:

        response = (
            apps_api.list_namespaced_stateful_set(
                namespace
            )
        )

        for statefulset in response.items:

            containers = get_containers(
                statefulset
            )

            for container in containers:

                scan_container(
                    results,
                    namespace,
                    "StatefulSet",
                    statefulset.metadata.name,
                    container,
                )

    except Exception:
        pass

    return results


# ============================================================
# SCAN DAEMONSETS
# ============================================================

def scan_daemonsets(
    apps_api,
    namespace,
):

    results = []

    try:

        response = (
            apps_api.list_namespaced_daemon_set(
                namespace
            )
        )

        for daemonset in response.items:

            containers = get_containers(
                daemonset
            )

            for container in containers:

                scan_container(
                    results,
                    namespace,
                    "DaemonSet",
                    daemonset.metadata.name,
                    container,
                )

    except Exception:
        pass

    return results


# ============================================================
# SCAN JOBS
# ============================================================

def scan_jobs(
    batch_api,
    namespace,
):

    results = []

    try:

        response = (
            batch_api.list_namespaced_job(
                namespace
            )
        )

        for job in response.items:

            try:

                containers = (
                    job.spec.template.spec.containers
                )

            except Exception:

                containers = []

            for container in containers:

                scan_container(
                    results,
                    namespace,
                    "Job",
                    job.metadata.name,
                    container,
                )

    except Exception:
        pass

    return results


# ============================================================
# SCAN CRONJOBS
# ============================================================

def scan_cronjobs(
    batch_api,
    namespace,
):

    results = []

    try:

        response = (
            batch_api.list_namespaced_cron_job(
                namespace
            )
        )

        for cronjob in response.items:

            try:

                containers = (
                    cronjob
                    .spec
                    .job_template
                    .spec
                    .template
                    .spec
                    .containers
                )

            except Exception:

                containers = []

            for container in containers:

                scan_container(
                    results,
                    namespace,
                    "CronJob",
                    cronjob.metadata.name,
                    container,
                )

    except Exception:
        pass

    return results


# ============================================================
# SCAN NAMESPACE
# ============================================================

def scan_namespace(
    core_api,
    apps_api,
    batch_api,
    namespace,
):

    results = []

    results.extend(
        scan_secrets(
            core_api,
            namespace,
        )
    )

    results.extend(
        scan_configmaps(
            core_api,
            namespace,
        )
    )

    results.extend(
        scan_deployments(
            apps_api,
            namespace,
        )
    )

    results.extend(
        scan_statefulsets(
            apps_api,
            namespace,
        )
    )

    results.extend(
        scan_daemonsets(
            apps_api,
            namespace,
        )
    )

    results.extend(
        scan_jobs(
            batch_api,
            namespace,
        )
    )

    results.extend(
        scan_cronjobs(
            batch_api,
            namespace,
        )
    )

    return results


# ============================================================
# GET NAMESPACES
# ============================================================

def get_namespaces(
    core_api,
):

    response = core_api.list_namespace()

    return sorted(
        [
            item.metadata.name
            for item in response.items
        ]
    )


# ============================================================
# RESOURCE TO YAML
# ============================================================

def resource_yaml(
    resource,
):

    return yaml.safe_dump(
        resource.to_dict(),
        sort_keys=False,
        default_flow_style=False,
    )


# ============================================================
# GET RESOURCE
# ============================================================

def get_resource_for_replacement(
    core_api,
    apps_api,
    batch_api,
    namespace,
    resource_type,
    resource_name,
):

    if resource_type == "Secret":

        return core_api.read_namespaced_secret(
            resource_name,
            namespace,
        )

    if resource_type == "ConfigMap":

        return core_api.read_namespaced_config_map(
            resource_name,
            namespace,
        )

    if resource_type == "Deployment":

        return apps_api.read_namespaced_deployment(
            resource_name,
            namespace,
        )

    if resource_type == "StatefulSet":

        return apps_api.read_namespaced_stateful_set(
            resource_name,
            namespace,
        )

    if resource_type == "DaemonSet":

        return apps_api.read_namespaced_daemon_set(
            resource_name,
            namespace,
        )

    if resource_type == "Job":

        return batch_api.read_namespaced_job(
            resource_name,
            namespace,
        )

    if resource_type == "CronJob":

        return batch_api.read_namespaced_cron_job(
            resource_name,
            namespace,
        )

    return None


# ============================================================
# CREATE BACKUP ZIP
# ============================================================

def create_backup_zip(
    backup_resources,
):

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:

        for item in backup_resources:

            filename = (
                f'{item["namespace"]}/'
                f'{item["resource_type"]}/'
                f'{item["resource_name"]}.yaml'
            )

            archive.writestr(
                filename,
                resource_yaml(
                    item["resource"]
                ),
            )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# REPLACE URL IN WORKLOAD
# ============================================================

def replace_in_container(
    container,
    old_url,
    new_url,
):

    changed = False

    # ENV
    if container.env:

        for env in container.env:

            if env.value and old_url in env.value:

                env.value = env.value.replace(
                    old_url,
                    new_url,
                )

                changed = True

    # COMMAND
    if container.command:

        for i, value in enumerate(
            container.command
        ):

            if old_url in value:

                container.command[i] = (
                    value.replace(
                        old_url,
                        new_url,
                    )
                )

                changed = True

    # ARGS
    if container.args:

        for i, value in enumerate(
            container.args
        ):

            if old_url in value:

                container.args[i] = (
                    value.replace(
                        old_url,
                        new_url,
                    )
                )

                changed = True

    return changed


# ============================================================
# APPLY REPLACEMENT
# ============================================================

def apply_replacement(
    core_api,
    apps_api,
    batch_api,
    namespace,
    resource_type,
    resource_name,
    old_url,
    new_url,
):

    # ========================================================
    # SECRET
    # ========================================================

    if resource_type == "Secret":

        resource = (
            core_api.read_namespaced_secret(
                resource_name,
                namespace,
            )
        )

        if not resource.data:
            return False

        changed = False

        new_data = dict(
            resource.data
        )

        for key, encoded_value in resource.data.items():

            try:

                decoded = (
                    base64.b64decode(
                        encoded_value
                    )
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

            except Exception:

                continue

            if old_url in decoded:

                replaced = decoded.replace(
                    old_url,
                    new_url,
                )

                new_data[key] = (
                    base64.b64encode(
                        replaced.encode()
                    ).decode()
                )

                changed = True

        if changed:

            core_api.patch_namespaced_secret(
                resource_name,
                namespace,
                {
                    "data": new_data
                },
            )

        return changed


    # ========================================================
    # CONFIGMAP
    # ========================================================

    if resource_type == "ConfigMap":

        resource = (
            core_api.read_namespaced_config_map(
                resource_name,
                namespace,
            )
        )

        if not resource.data:
            return False

        changed = False

        new_data = dict(
            resource.data
        )

        for key, value in resource.data.items():

            if (
                isinstance(value, str)
                and old_url in value
            ):

                new_data[key] = value.replace(
                    old_url,
                    new_url,
                )

                changed = True

        if changed:

            core_api.patch_namespaced_config_map(
                resource_name,
                namespace,
                {
                    "data": new_data
                },
            )

        return changed


    # ========================================================
    # DEPLOYMENT
    # ========================================================

    if resource_type == "Deployment":

        resource = (
            apps_api.read_namespaced_deployment(
                resource_name,
                namespace,
            )
        )

        containers = (
            resource.spec.template.spec.containers
        )

        changed = False

        for container in containers:

            if replace_in_container(
                container,
                old_url,
                new_url,
            ):

                changed = True

        if changed:

            apps_api.patch_namespaced_deployment(
                resource_name,
                namespace,
                {
                    "spec": {
                        "template": resource
                        .spec
                        .template
                        .to_dict()
                    }
                },
            )

        return changed


    # ========================================================
    # STATEFULSET
    # ========================================================

    if resource_type == "StatefulSet":

        resource = (
            apps_api.read_namespaced_stateful_set(
                resource_name,
                namespace,
            )
        )

        containers = (
            resource.spec.template.spec.containers
        )

        changed = False

        for container in containers:

            if replace_in_container(
                container,
                old_url,
                new_url,
            ):

                changed = True

        if changed:

            apps_api.patch_namespaced_stateful_set(
                resource_name,
                namespace,
                {
                    "spec": {
                        "template": resource
                        .spec
                        .template
                        .to_dict()
                    }
                },
            )

        return changed


    # ========================================================
    # DAEMONSET
    # ========================================================

    if resource_type == "DaemonSet":

        resource = (
            apps_api.read_namespaced_daemon_set(
                resource_name,
                namespace,
            )
        )

        containers = (
            resource.spec.template.spec.containers
        )

        changed = False

        for container in containers:

            if replace_in_container(
                container,
                old_url,
                new_url,
            ):

                changed = True

        if changed:

            apps_api.patch_namespaced_daemon_set(
                resource_name,
                namespace,
                {
                    "spec": {
                        "template": resource
                        .spec
                        .template
                        .to_dict()
                    }
                },
            )

        return changed


    # ========================================================
    # JOB
    # ========================================================

    if resource_type == "Job":

        resource = (
            batch_api.read_namespaced_job(
                resource_name,
                namespace,
            )
        )

        containers = (
            resource
            .spec
            .template
            .spec
            .containers
        )

        changed = False

        for container in containers:

            if replace_in_container(
                container,
                old_url,
                new_url,
            ):

                changed = True

        if changed:

            batch_api.patch_namespaced_job(
                resource_name,
                namespace,
                {
                    "spec": {
                        "template": resource
                        .spec
                        .template
                        .to_dict()
                    }
                },
            )

        return changed


    # ========================================================
    # CRONJOB
    # ========================================================

    if resource_type == "CronJob":

        resource = (
            batch_api.read_namespaced_cron_job(
                resource_name,
                namespace,
            )
        )

        template = (
            resource
            .spec
            .job_template
            .spec
            .template
        )

        containers = (
            template
            .spec
            .containers
        )

        changed = False

        for container in containers:

            if replace_in_container(
                container,
                old_url,
                new_url,
            ):

                changed = True

        if changed:

            batch_api.patch_namespaced_cron_job(
                resource_name,
                namespace,
                {
                    "spec": {
                        "job_template": (
                            resource
                            .spec
                            .job_template
                            .to_dict()
                        )
                    }
                },
            )

        return changed


    return False


# ============================================================
# MAIN PAGE
# ============================================================

def render_db_string():

    st.markdown(
        """
        <style>

        .db-title {
            font-size: 36px;
            font-weight: 800;
            color: #18213d;
        }

        .db-subtitle {
            color: #64748b;
            font-size: 16px;
            margin-bottom: 25px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="db-title">DB String</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="db-subtitle">
            Find and safely replace MongoDB connection strings
            by Kubernetes namespace.
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # KUBECONFIG
    # ========================================================

    kube_file = st.file_uploader(
        "Upload kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf",
        ],
        key="db_kubeconfig",
    )

    if kube_file is None:

        st.info(
            "Upload a kubeconfig file to scan the cluster."
        )

        return


    # ========================================================
    # CONNECT
    # ========================================================

    try:

        api_client = create_kubernetes_client(
            kube_file.getvalue()
        )

        core_api = client.CoreV1Api(
            api_client
        )

        apps_api = client.AppsV1Api(
            api_client
        )

        batch_api = client.BatchV1Api(
            api_client
        )

        core_api.get_api_resources()

    except Exception as exc:

        st.error(
            f"Failed to connect to Kubernetes cluster: {exc}"
        )

        return


    st.success(
        "Connected to Kubernetes cluster."
    )


    # ========================================================
    # NAMESPACES
    # ========================================================

    try:

        namespace_names = get_namespaces(
            core_api
        )

    except Exception as exc:

        st.error(
            f"Unable to retrieve namespaces: {exc}"
        )

        return


    if not namespace_names:

        st.warning(
            "No namespaces found."
        )

        return


    namespace_options = (
        ["All Namespaces"] +
        namespace_names
    )


    selected_namespace = st.selectbox(
        "🔎 Select Namespace",
        namespace_options,
        key="db_namespace",
    )


    # ========================================================
    # SCAN BUTTON
    # ========================================================

    if st.button(
        "🔎 Find MongoDB DB Strings",
        use_container_width=True,
        type="primary",
        key="find_db_strings",
    ):

        if selected_namespace == "All Namespaces":

            namespaces_to_scan = namespace_names

        else:

            namespaces_to_scan = [
                selected_namespace
            ]


        all_results = []

        progress = st.progress(0)

        status = st.empty()

        total = len(
            namespaces_to_scan
        )


        for index, namespace in enumerate(
            namespaces_to_scan
        ):

            status.write(
                f"Scanning namespace: `{namespace}`"
            )

            namespace_results = scan_namespace(
                core_api,
                apps_api,
                batch_api,
                namespace,
            )

            all_results.extend(
                namespace_results
            )

            progress.progress(
                int(
                    (
                        (index + 1)
                        / total
                    ) * 100
                )
            )


        status.empty()
        progress.empty()


        # Remove duplicates

        unique_results = []

        seen = set()

        for item in all_results:

            key = (
                item["Namespace"],
                item["Resource Type"],
                item["Resource Name"],
                item["Key"],
                item["DB String"],
            )

            if key not in seen:

                seen.add(key)

                unique_results.append(
                    item
                )


        st.session_state.db_results = (
            unique_results
        )

        st.session_state.db_preview = False


    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    if "db_results" not in st.session_state:

        return


    results = (
        st.session_state.db_results
    )


    if not results:

        st.warning(
            "No MongoDB connection strings found."
        )

        return


    df = pd.DataFrame(
        results
    )


    st.success(
        f"Found {len(df)} MongoDB connection string(s)."
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    st.subheader(
        "DB Strings by Namespace"
    )


    namespace_summary = (
        df.groupby(
            "Namespace"
        )
        .size()
        .reset_index(
            name="DB String Count"
        )
    )


    st.dataframe(
        namespace_summary,
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # RESULTS
    # ========================================================

    st.subheader(
        "MongoDB Connection Strings"
    )


    # IMPORTANT:
    # Key column is now displayed.

    display_columns = [
        "Namespace",
        "Resource Type",
        "Resource Name",
        "Key",
        "DB String",
    ]


    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # EXCEL DOWNLOAD
    # ========================================================

    excel_buffer = io.BytesIO()


    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:

        namespace_summary.to_excel(
            writer,
            index=False,
            sheet_name="Namespace Summary",
        )

        df[display_columns].to_excel(
            writer,
            index=False,
            sheet_name="DB Strings",
        )


    st.download_button(
        "⬇️ Download Excel",
        data=excel_buffer.getvalue(),
        file_name="kubernetes_db_strings.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


    # ============================================================
    # UPDATE KEY VALUE
    # ============================================================

    st.divider()

    st.subheader(
        "🔄 Update Key Value"
    )

    st.warning(
        "This operation can modify Kubernetes resources. "
        "Download the backup before applying changes."
    )


    # ============================================================
    # RESOURCE SELECTION
    # ============================================================

    st.markdown("### Select Resource")


    # Create readable resource list

    resource_options = []

    for index, row in df.iterrows():

        resource_options.append(
            f"{index} | "
            f"{row['Namespace']} | "
            f"{row['Resource Type']} | "
            f"{row['Resource Name']} | "
            f"{row['Key']}"
        )


    selected_resource = st.selectbox(
        "Select Resource / Key",
        resource_options,
        key="selected_db_resource",
    )


    # ============================================================
    # GET SELECTED ROW
    # ============================================================

    selected_index = int(
        selected_resource.split("|")[0].strip()
    )

    selected_row = df.iloc[
        selected_index
    ]


    selected_namespace = selected_row[
        "Namespace"
    ]

    selected_resource_type = selected_row[
        "Resource Type"
    ]

    selected_resource_name = selected_row[
        "Resource Name"
    ]

    selected_key = selected_row[
        "Key"
    ]

    current_value = selected_row[
        "DB String"
    ]


    # ============================================================
    # DISPLAY SELECTED RESOURCE
    # ============================================================

    col1, col2 = st.columns(2)


    with col1:

        st.text_input(
            "Namespace",
            value=selected_namespace,
            disabled=True,
            key="selected_namespace_display",
        )


    with col2:

        st.text_input(
            "Resource Type",
            value=selected_resource_type,
            disabled=True,
            key="selected_resource_type_display",
        )


    col3, col4 = st.columns(2)


    with col3:

        st.text_input(
            "Resource Name",
            value=selected_resource_name,
            disabled=True,
            key="selected_resource_name_display",
        )


    with col4:

        st.text_input(
            "Key",
            value=selected_key,
            disabled=True,
            key="selected_key_display",
        )


    # ============================================================
    # CURRENT VALUE
    # ============================================================

    st.markdown("### Current Value")

    st.text_area(
        "Current Value",
        value=current_value,
        height=100,
        disabled=True,
        key="current_db_value",
    )


    # ============================================================
    # NEW VALUE
    # ============================================================

    st.markdown("### New Value")

    new_value = st.text_area(
        "Enter New Value",
        placeholder="mongodb://new-host:27017/database",
        height=120,
        key="new_db_value",
    )


    # ============================================================
    # PREVIEW
    # ============================================================

    if st.button(
        "🔎 Preview Change",
        use_container_width=True,
        type="primary",
        key="preview_key_change",
    ):

        if not new_value.strip():

            st.error(
                "Please enter the new value."
            )

        elif new_value.strip() == current_value.strip():

            st.error(
                "New value is the same as the current value."
            )

        else:

            preview_data = pd.DataFrame(
                [
                    {
                        "Namespace": selected_namespace,
                        "Resource Type": selected_resource_type,
                        "Resource Name": selected_resource_name,
                        "Key": selected_key,
                        "Current Value": current_value,
                        "New Value": new_value,
                    }
                ]
            )

            st.session_state.key_update_preview = (
                preview_data
            )

            st.session_state.key_update_ready = True


    # ============================================================
    # SHOW PREVIEW
    # ============================================================

    if st.session_state.get(
        "key_update_ready",
        False,
    ):

        preview_data = (
            st.session_state.key_update_preview
        )


        st.divider()

        st.subheader(
            "🔎 Preview Change"
        )


        st.dataframe(
            preview_data,
            use_container_width=True,
            hide_index=True,
        )


        # ========================================================
        # GET RESOURCE FOR BACKUP
        # ========================================================

        try:

            backup_resource = (
                get_resource_for_replacement(
                    core_api,
                    apps_api,
                    batch_api,
                    selected_namespace,
                    selected_resource_type,
                    selected_resource_name,
                )
            )

        except Exception as exc:

            backup_resource = None

            st.error(
                f"Unable to read resource: {exc}"
            )


        # ========================================================
        # BACKUP
        # ========================================================

        st.divider()

        st.subheader(
            "💾 Backup Before Apply"
        )


        if backup_resource:

            backup_zip = create_backup_zip(
                [
                    {
                        "namespace": selected_namespace,
                        "resource_type": selected_resource_type,
                        "resource_name": selected_resource_name,
                        "resource": backup_resource,
                    }
                ]
            )


            st.download_button(
                "⬇️ Download Backup YAML",
                data=backup_zip,
                file_name=(
                    f"{selected_resource_name}_backup.zip"
                ),
                mime="application/zip",
                use_container_width=True,
                key="download_single_backup",
            )


        # ========================================================
        # CONFIRMATION
        # ========================================================

        st.divider()

        st.subheader(
            "⚠️ Apply Change"
        )


        confirm_update = st.checkbox(
            "I have reviewed the current and new values "
            "and downloaded the backup.",
            key="confirm_key_update",
        )


        if st.button(
            "⚠️ Apply Key Value Update",
            use_container_width=True,
            type="primary",
            key="apply_key_update",
        ):

            if not confirm_update:

                st.error(
                    "Please confirm the change before applying."
                )

            else:

                try:

                    # =================================================
                    # SECRET
                    # =================================================

                    if selected_resource_type == "Secret":

                        secret = (
                            core_api.read_namespaced_secret(
                                selected_resource_name,
                                selected_namespace,
                            )
                        )

                        if not secret.data:

                            raise Exception(
                                "Secret does not contain data."
                            )


                        if selected_key not in secret.data:

                            raise Exception(
                                f"Key '{selected_key}' "
                                "was not found in the Secret."
                            )


                        encoded_value = secret.data[
                            selected_key
                        ]


                        # Base64 encode new value

                        encoded_new_value = (
                            base64.b64encode(
                                new_value.encode()
                            ).decode()
                        )


                        core_api.patch_namespaced_secret(
                            selected_resource_name,
                            selected_namespace,
                            {
                                "data": {
                                    selected_key:
                                        encoded_new_value
                                }
                            },
                        )


                    # =================================================
                    # CONFIGMAP
                    # =================================================

                    elif selected_resource_type == "ConfigMap":

                        configmap = (
                            core_api.read_namespaced_config_map(
                                selected_resource_name,
                                selected_namespace,
                            )
                        )


                        if not configmap.data:

                            raise Exception(
                                "ConfigMap does not contain data."
                            )


                        if selected_key not in configmap.data:

                            raise Exception(
                                f"Key '{selected_key}' "
                                "was not found in the ConfigMap."
                            )


                        core_api.patch_namespaced_config_map(
                            selected_resource_name,
                            selected_namespace,
                            {
                                "data": {
                                    selected_key:
                                        new_value
                                }
                            },
                        )


                    # =================================================
                    # DEPLOYMENT
                    # =================================================

                    elif selected_resource_type == "Deployment":

                        deployment = (
                            apps_api.read_namespaced_deployment(
                                selected_resource_name,
                                selected_namespace,
                            )
                        )

                        containers = (
                            deployment
                            .spec
                            .template
                            .spec
                            .containers
                        )


                        changed = False


                        for container in containers:

                            if container.env:

                                for env in container.env:

                                    if env.name == selected_key:

                                        env.value = new_value

                                        changed = True


                        if not changed:

                            raise Exception(
                                f"Environment variable "
                                f"'{selected_key}' "
                                "was not found."
                            )


                        apps_api.patch_namespaced_deployment(
                            selected_resource_name,
                            selected_namespace,
                            {
                                "spec": {
                                    "template":
                                        deployment
                                        .spec
                                        .template
                                        .to_dict()
                                }
                            },
                        )


                    # =================================================
                    # STATEFULSET
                    # =================================================

                    elif selected_resource_type == "StatefulSet":

                        statefulset = (
                            apps_api.read_namespaced_stateful_set(
                                selected_resource_name,
                                selected_namespace,
                            )
                        )

                        containers = (
                            statefulset
                            .spec
                            .template
                            .spec
                            .containers
                        )


                        changed = False


                        for container in containers:

                            if container.env:

                                for env in container.env:

                                    if env.name == selected_key:

                                        env.value = new_value

                                        changed = True


                        if not changed:

                            raise Exception(
                                f"Environment variable "
                                f"'{selected_key}' "
                                "was not found."
                            )


                        apps_api.patch_namespaced_stateful_set(
                            selected_resource_name,
                            selected_namespace,
                            {
                                "spec": {
                                    "template":
                                        statefulset
                                        .spec
                                        .template
                                        .to_dict()
                                }
                            },
                        )


                    # =================================================
                    # DAEMONSET
                    # =================================================

                    elif selected_resource_type == "DaemonSet":

                        daemonset = (
                            apps_api.read_namespaced_daemon_set(
                                selected_resource_name,
                                selected_namespace,
                            )
                        )

                        containers = (
                            daemonset
                            .spec
                            .template
                            .spec
                            .containers
                        )


                        changed = False


                        for container in containers:

                            if container.env:

                                for env in container.env:

                                    if env.name == selected_key:

                                        env.value = new_value

                                        changed = True


                        if not changed:

                            raise Exception(
                                f"Environment variable "
                                f"'{selected_key}' "
                                "was not found."
                            )


                        apps_api.patch_namespaced_daemon_set(
                            selected_resource_name,
                            selected_namespace,
                            {
                                "spec": {
                                    "template":
                                        daemonset
                                        .spec
                                        .template
                                        .to_dict()
                                }
                            },
                        )


                    # =================================================
                    # UNSUPPORTED
                    # =================================================

                    else:

                        raise Exception(
                            f"Direct key update is currently "
                            f"not supported for {selected_resource_type}."
                        )


                    st.success(
                        f"Successfully updated key "
                        f"'{selected_key}' in "
                        f"{selected_resource_type}/"
                        f"{selected_resource_name}."
                    )


                    st.info(
                        "Run the DB String scan again to verify "
                        "the updated value."
                    )


                    st.session_state.key_update_ready = False


                except Exception as exc:

                    st.error(
                        f"Failed to update key: {exc}"
                    )