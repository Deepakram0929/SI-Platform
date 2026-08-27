import streamlit as st
import tempfile
import os
import pandas as pd
from kubernetes import client, config


# ============================================================
# PAGE CONFIG / CONSTANTS
# ============================================================

ENVIRONMENTS = [
    "UAT",
    "BLUE",
    "DEV",
    "Green",
    "STAGING",
    "Preprod",
    "Prod",
]

RESOURCE_TYPES = [
    "Deployment",
    "StatefulSet",
]

RESOURCE_FIELDS = [
    "CPU Request",
    "Memory Request",
    "CPU Limit",
    "Memory Limit",
]

# Used only for bulk-selection filtering. It never hides comparison rows.
SYNC_OPTIONS = RESOURCE_FIELDS.copy()


# ============================================================
# KUBECONFIG HELPERS
# ============================================================

def save_uploaded_kubeconfig(uploaded_file):
    """
    Save uploaded kubeconfig temporarily and return its path.
    """

    if uploaded_file is None:
        return None

    suffix = ".yaml"

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    temp.write(uploaded_file.getvalue())
    temp.close()

    return temp.name


def create_api_client(kubeconfig_path):
    """
    Create Kubernetes API client from kubeconfig.
    """

    config.load_kube_config(
        config_file=kubeconfig_path
    )

    return client.ApiClient()


# ============================================================
# RESOURCE HELPERS
# ============================================================

def get_workloads(api_client, namespace, resource_type):
    """
    Get Deployment / StatefulSet resources.
    """

    apps_api = client.AppsV1Api(api_client)

    if resource_type == "Deployment":

        result = apps_api.list_namespaced_deployment(
            namespace=namespace
        )

    else:

        result = apps_api.list_namespaced_stateful_set(
            namespace=namespace
        )

    return result.items


def get_workloads_for_namespaces(api_client, namespaces, resource_type):
    """
    Fetch workloads for all selected namespaces efficiently.

    Preferred path: one cluster-wide API call per resource type.
    Fallback: namespace-by-namespace calls when the service account does
    not have cluster-wide list permission.
    """
    namespace_set = set(namespaces or [])
    if not namespace_set:
        return []

    apps_api = client.AppsV1Api(api_client)

    try:
        if resource_type == "Deployment":
            result = apps_api.list_deployment_for_all_namespaces()
        else:
            result = apps_api.list_stateful_set_for_all_namespaces()

        return [
            item for item in result.items
            if item.metadata.namespace in namespace_set
        ]

    except Exception:
        # Preserve compatibility with namespace-scoped RBAC.
        items = []
        for namespace in namespaces:
            items.extend(
                get_workloads(api_client, namespace, resource_type)
            )
        return items


def get_namespaces(api_client):
    """
    Get namespaces from cluster.
    """

    core_api = client.CoreV1Api(api_client)

    result = core_api.list_namespace()

    return sorted(
        [
            item.metadata.name
            for item in result.items
        ]
    )


def get_container_resources(container):
    """Extract all four Kubernetes CPU/memory request/limit values."""

    resources = container.resources

    requests = {}
    limits = {}

    if resources:
        requests = resources.requests or {}
        limits = resources.limits or {}

    return {
        "CPU Request": requests.get("cpu", "") or "-",
        "Memory Request": requests.get("memory", "") or "-",
        "CPU Limit": limits.get("cpu", "") or "-",
        "Memory Limit": limits.get("memory", "") or "-",
    }


# ============================================================
# EXTRACT RESOURCE INFORMATION
# ============================================================

def extract_resources(
    api_client,
    namespace,
    resource_type
):
    """Extract every container and all four CPU/memory fields."""

    workloads = get_workloads(
        api_client,
        namespace,
        resource_type
    )

    rows = []

    for workload in workloads:
        workload_name = workload.metadata.name

        containers = (
            workload.spec
            .template
            .spec
            .containers
            or []
        )

        for container in containers:
            values = get_container_resources(container)

            rows.append({
                "Resource Type": resource_type,
                "Namespace": namespace,
                "Workload": workload_name,
                "Container": container.name,
                **values,
            })

    return rows


# ============================================================
# BUILD COMPARISON
# ============================================================

def extract_resources_for_namespaces(
    api_client,
    namespaces,
    resource_type,
):
    """Extract all selected namespaces with one API list where possible."""
    workloads = get_workloads_for_namespaces(
        api_client,
        namespaces,
        resource_type,
    )

    rows = []

    for workload in workloads:
        namespace = workload.metadata.namespace
        workload_name = workload.metadata.name

        containers = (
            workload.spec.template.spec.containers or []
        )

        for container in containers:
            values = get_container_resources(container)

            rows.append({
                "Resource Type": resource_type,
                "Namespace": namespace,
                "Workload": workload_name,
                "Container": container.name,
                **values,
            })

    return rows


def build_comparison(source_rows, destination_rows):
    """Compare all four resource fields independently."""

    destination_map = {}

    for row in destination_rows:
        key = (
            row["Resource Type"],
            row["Namespace"],
            row["Workload"],
            row["Container"],
        )
        destination_map[key] = row

    comparison = []

    for source in source_rows:
        key = (
            source["Resource Type"],
            source["Namespace"],
            source["Workload"],
            source["Container"],
        )

        destination = destination_map.get(key)

        result = {
            "Resource Type": source["Resource Type"],
            "Namespace": source["Namespace"],
            "Workload": source["Workload"],
            "Container": source["Container"],
        }

        for field in RESOURCE_FIELDS:
            source_value = source.get(field, "-") or "-"
            destination_value = (
                destination.get(field, "-") or "-"
                if destination else "Not Found"
            )

            status = (
                "Not Found"
                if destination is None
                else ("Same" if source_value == destination_value else "Different")
            )

            result[f"Source {field}"] = source_value
            result[f"Destination {field}"] = destination_value
            result[f"{field} Status"] = status

        comparison.append(result)

    return comparison


# ============================================================
# APPLY RESOURCE UPDATE
# ============================================================

def update_workload(
    api_client,
    namespace,
    resource_type,
    workload_name,
    container_name,
    cpu_request=None,
    memory_request=None,
    cpu_limit=None,
    memory_limit=None,
):
    """Update only the selected CPU/memory request/limit fields."""

    apps_api = client.AppsV1Api(api_client)

    if resource_type == "Deployment":
        workload = apps_api.read_namespaced_deployment(
            name=workload_name,
            namespace=namespace,
        )
    else:
        workload = apps_api.read_namespaced_stateful_set(
            name=workload_name,
            namespace=namespace,
        )

    target_container = next(
        (
            c for c in workload.spec.template.spec.containers
            if c.name == container_name
        ),
        None,
    )

    if target_container is None:
        raise Exception(f"Container '{container_name}' not found")

    if target_container.resources is None:
        target_container.resources = client.V1ResourceRequirements()

    if target_container.resources.requests is None:
        target_container.resources.requests = {}

    if target_container.resources.limits is None:
        target_container.resources.limits = {}

    updates = {
        "cpu_request": (target_container.resources.requests, "cpu", cpu_request),
        "memory_request": (target_container.resources.requests, "memory", memory_request),
        "cpu_limit": (target_container.resources.limits, "cpu", cpu_limit),
        "memory_limit": (target_container.resources.limits, "memory", memory_limit),
    }

    for _, (target_map, key, value) in updates.items():
        if value is None:
            continue
        if value == "-":
            target_map.pop(key, None)
        else:
            target_map[key] = value

    if resource_type == "Deployment":
        return apps_api.patch_namespaced_deployment(
            name=workload_name,
            namespace=namespace,
            body=workload,
        )

    return apps_api.patch_namespaced_stateful_set(
        name=workload_name,
        namespace=namespace,
        body=workload,
    )


# ============================================================
# PAGE
# ============================================================

def render_cpu_memory():

    # ========================================================
    # CSS
    # ========================================================

    st.markdown(
        """
        <style>
        .cm-title {
            font-size: 34px;
            font-weight: 750;
            color: #18213d;
            margin-bottom: 5px;
        }

        .cm-subtitle {
            font-size: 15px;
            color: #667085;
            margin-bottom: 20px;
        }

        .cm-section {
            font-size: 20px;
            font-weight: 700;
            color: #18213d;
            margin-top: 18px;
            margin-bottom: 10px;
        }

        .cm-info {
            background: #f5f9ff;
            border: 1px solid #d8e7ff;
            border-radius: 10px;
            padding: 13px 16px;
            margin-bottom: 16px;
        }

        .cm-warning {
            background: #fff8eb;
            border: 1px solid #f6d99a;
            border-radius: 10px;
            padding: 14px 16px;
            margin: 12px 0;
        }

        .cm-source {
            background: #f1fff6;
            border: 1px solid #9be5b5;
            border-radius: 9px;
            padding: 12px 15px;
        }

        .cm-destination {
            background: #fff4f5;
            border: 1px solid #f0aab3;
            border-radius: 9px;
            padding: 12px 15px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # SESSION STATE
    # ========================================================

    defaults = {
        "cm_source_env": "UAT",
        "cm_destination_env": "Prod",
        "cm_source_client": None,
        "cm_destination_client": None,
        "cm_source_signature": None,
        "cm_destination_signature": None,
        "cm_comparison_v6": None,
        "cm_source_rows": [],
        "cm_destination_rows": [],
        "cm_global_selected": [],
        "cm_global_revision": 0,
        "cm_pending_update": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="cm-title">⚙️ CPU &amp; Memory Comparator</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="cm-subtitle">
        Compare CPU and memory requests between Kubernetes environments
        and selectively synchronize source values to the destination.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    st.markdown(
        '<div class="cm-section">🌐 Environment</div>',
        unsafe_allow_html=True,
    )

    env_col1, env_col2 = st.columns(2)

    with env_col1:
        source_current = st.session_state.get("cm_source_env", "UAT")
        source_index = (
            ENVIRONMENTS.index(source_current)
            if source_current in ENVIRONMENTS
            else 0
        )

        source_env = st.selectbox(
            "Source",
            ENVIRONMENTS,
            index=source_index,
            key="cm_source_env_select",
        )

    with env_col2:
        destination_options = [
            env for env in ENVIRONMENTS if env != source_env
        ]

        destination_current = st.session_state.get(
            "cm_destination_env",
            "Prod",
        )

        destination_index = (
            destination_options.index(destination_current)
            if destination_current in destination_options
            else 0
        )

        destination_env = st.selectbox(
            "Destination",
            destination_options,
            index=destination_index,
            key="cm_destination_env_select",
        )

    environment_changed = (
        source_env != st.session_state.get("cm_source_env")
        or destination_env != st.session_state.get("cm_destination_env")
    )

    if environment_changed:
        st.session_state.cm_source_env = source_env
        st.session_state.cm_destination_env = destination_env

        # Do not allow an old comparison/update queue to be applied to
        # a newly selected environment pair.
        st.session_state.cm_source_client = None
        st.session_state.cm_destination_client = None
        st.session_state.cm_source_signature = None
        st.session_state.cm_destination_signature = None
        st.session_state.cm_comparison_v6 = None
        st.session_state.cm_source_rows = []
        st.session_state.cm_destination_rows = []
        st.session_state.cm_global_selected = []
        st.session_state.cm_global_revision += 1
        st.session_state.cm_pending_update = False

        for key in list(st.session_state.keys()):
            if (
                str(key).startswith("cm_local_selected_")
                or str(key).startswith("cm_editor_")
                or str(key).startswith("cm_select_")
            ):
                del st.session_state[key]

    # Transfer direction
    direction_left, arrow_col, direction_right = st.columns([1, 0.15, 1])

    with direction_left:
        st.success(f"🟢 {source_env}")

    with arrow_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("➡️")

    with direction_right:
        st.error(f"🔴 {destination_env}")

    # ========================================================
    # KUBECONFIG UPLOAD
    # ========================================================

    st.markdown(
        '<div class="cm-section">🔐 Kubernetes Environments</div>',
        unsafe_allow_html=True,
    )

    file_col1, file_col2 = st.columns(2, gap="large")

    with file_col1:
        st.markdown(
            f'<div class="cm-source"><b>🟢 {source_env} Cluster</b></div>',
            unsafe_allow_html=True,
        )

        source_file = st.file_uploader(
            f"Upload {source_env} kubeconfig",
            type=["yaml", "yml", "conf"],
            key="cm_source_kubeconfig",
        )

    with file_col2:
        st.markdown(
            f'<div class="cm-destination"><b>🔴 {destination_env} Cluster</b></div>',
            unsafe_allow_html=True,
        )

        destination_file = st.file_uploader(
            f"Upload {destination_env} kubeconfig",
            type=["yaml", "yml", "conf"],
            key="cm_destination_kubeconfig",
        )

    if not source_file or not destination_file:
        st.info(
            f"Upload both {source_env} and {destination_env} kubeconfig files to continue."
        )
        return

    # ========================================================
    # CONNECT CLIENTS
    # ========================================================

    source_signature = (
        source_env,
        source_file.name,
        len(source_file.getvalue()),
    )
    destination_signature = (
        destination_env,
        destination_file.name,
        len(destination_file.getvalue()),
    )

    try:
        if (
            st.session_state.cm_source_client is None
            or st.session_state.cm_source_signature != source_signature
        ):
            source_path = save_uploaded_kubeconfig(source_file)
            st.session_state.cm_source_client = create_api_client(
                source_path
            )
            st.session_state.cm_source_signature = source_signature

        if (
            st.session_state.cm_destination_client is None
            or st.session_state.cm_destination_signature
            != destination_signature
        ):
            destination_path = save_uploaded_kubeconfig(
                destination_file
            )
            st.session_state.cm_destination_client = create_api_client(
                destination_path
            )
            st.session_state.cm_destination_signature = (
                destination_signature
            )

    except Exception as exc:
        st.error(f"Unable to load kubeconfig: {exc}")
        return

    source_client = st.session_state.cm_source_client
    destination_client = st.session_state.cm_destination_client

    # ========================================================
    # NAMESPACE
    # ========================================================

    st.markdown(
        '<div class="cm-section">📁 Namespace</div>',
        unsafe_allow_html=True,
    )

    try:
        namespaces = get_namespaces(source_client)
    except Exception as exc:
        st.error(
            f"Unable to retrieve namespaces from {source_env}: {exc}"
        )
        return

    if not namespaces:
        st.warning(f"No namespaces found in {source_env}.")
        return

    selected_namespaces = st.multiselect(
        "Select namespaces",
        namespaces,
        key="cm_namespaces_v6",
        help=(
            "Select one or more namespaces. Each selected namespace is "
            "compared one by one, like the Environment Comparator."
        ),
    )

    if not selected_namespaces:
        st.info("Select at least one namespace to continue.")
        return

    # ========================================================
    # RESOURCE TYPE
    # ========================================================

    st.markdown(
        '<div class="cm-section">📦 Resource Type</div>',
        unsafe_allow_html=True,
    )

    selected_types = st.multiselect(
        "Select resource types",
        RESOURCE_TYPES,
        default=["Deployment", "StatefulSet"],
        key="cm_resource_types",
    )

    if not selected_types:
        st.warning("Select at least one resource type.")
        return

    # ========================================================
    # EXTRACT
    # ========================================================

    if st.button(
        f"🔍 Extract {source_env} → {destination_env}",
        type="primary",
        use_container_width=True,
        key="cm_extract",
    ):

        source_rows = []
        destination_rows = []

        with st.spinner(
            f"Extracting CPU & Memory efficiently from {source_env} and {destination_env}..."
        ):
            try:
                for resource_type in selected_types:
                    # One API call per environment/resource type instead of
                    # one call per namespace, when cluster-wide list RBAC
                    # is available. Namespace-scoped RBAC automatically
                    # falls back to the original method.
                    source_rows.extend(
                        extract_resources_for_namespaces(
                            source_client,
                            selected_namespaces,
                            resource_type,
                        )
                    )

                    destination_rows.extend(
                        extract_resources_for_namespaces(
                            destination_client,
                            selected_namespaces,
                            resource_type,
                        )
                    )

                comparison = build_comparison(
                    source_rows,
                    destination_rows,
                )

                # build_comparison already stores Source/Destination values
                # for all four resource fields. No legacy UAT/PROD renaming
                # is required here.

                st.session_state.cm_comparison_v6 = comparison
                st.session_state.cm_source_rows = source_rows
                st.session_state.cm_destination_rows = destination_rows

                # A new scan invalidates old local/global selections.
                st.session_state.cm_global_selected = []
                st.session_state.cm_global_revision += 1
                st.session_state.cm_pending_update = False

                for key in list(st.session_state.keys()):
                    if (
                        str(key).startswith("cm_local_selected_")
                        or str(key).startswith("cm_editor_")
                        or str(key).startswith("cm_select_")
                    ):
                        del st.session_state[key]

                st.success(
                    f"Extracted {len(source_rows)} source entries "
                    f"and {len(destination_rows)} destination entries."
                )

            except Exception as exc:
                st.error(f"Extraction failed: {exc}")

    comparison = st.session_state.get("cm_comparison_v6")

    if not comparison:
        return


    # ========================================================
    # RESULTS / SUMMARY
    # ========================================================

    st.markdown(
        '<div class="cm-section">📊 CPU &amp; Memory Comparison</div>',
        unsafe_allow_html=True,
    )

    total = len(comparison)
    cpu_different = sum(
        1 for row in comparison
        if row.get("CPU Request Status") == "Different"
        or row.get("CPU Limit Status") == "Different"
    )
    memory_different = sum(
        1 for row in comparison
        if row.get("Memory Request Status") == "Different"
        or row.get("Memory Limit Status") == "Different"
    )
    not_found = sum(
        1 for row in comparison
        if all(row.get(f"{field} Status") == "Not Found" for field in RESOURCE_FIELDS)
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Resources", total)
    c2.metric("CPU Differences", cpu_different)
    c3.metric("Memory Differences", memory_different)
    c4.metric(f"Not Found in {destination_env}", not_found)

    st.markdown(
        f"""
        <div class="cm-info">
        <b>{source_env} → {destination_env}</b><br>
        The comparison always shows all four Kubernetes resource fields:
        CPU Request, Memory Request, CPU Limit and Memory Limit.<br>
        Only checked rows are added to Global Update. The selected source
        value is written to the destination while all unselected resource
        fields remain unchanged.
        </div>
        """,
        unsafe_allow_html=True,
    )

    sync_options = st.multiselect(
        "Sync options (used for Select All DIFF)",
        SYNC_OPTIONS,
        default=RESOURCE_FIELDS,
        key="cm_sync_options_v5",
    )

    # A workload is displayed when at least one of the four fields differs.
    # Sync options never hide the four comparison rows.
    actionable_rows = []
    for index, row in enumerate(comparison):
        available = [
            field for field in RESOURCE_FIELDS
            if row.get(f"{field} Status") == "Different"
            and row.get(f"Destination {field}") != "Not Found"
        ]
        if available:
            actionable_rows.append((index, row, available))

    if not actionable_rows:
        st.success(
            f"No CPU/Memory differences require an update from "
            f"{source_env} to {destination_env}."
        )
        return

    quick1, quick2 = st.columns(2)

    with quick1:
        if st.button(
            "☑ Select All DIFF",
            use_container_width=True,
            key=f"cm_select_all_diff_{st.session_state.cm_global_revision}",
        ):
            for index, row, available in actionable_rows:
                local_key = (
                    f"cm_local_selected_{row['Namespace']}_"
                    f"{row['Resource Type']}_{row['Workload']}_"
                    f"{row['Container']}"
                )
                selected = set(st.session_state.get(local_key, []))
                selected.update(
                    field for field in available if field in sync_options
                )
                st.session_state[local_key] = sorted(selected)
            st.session_state.cm_global_revision += 1
            st.rerun()

    with quick2:
        if st.button(
            "☐ Clear All Selection",
            use_container_width=True,
            key=f"cm_clear_all_{st.session_state.cm_global_revision}",
        ):
            for key in list(st.session_state.keys()):
                if str(key).startswith("cm_local_selected_"):
                    del st.session_state[key]
            st.session_state.cm_global_revision += 1
            st.rerun()

    # ========================================================
    # ONE BLOCK PER NAMESPACE / WORKLOAD / CONTAINER
    # ========================================================

    for item_index, (index, row, available_changes) in enumerate(actionable_rows):
        local_key = (
            f"cm_local_selected_{row['Namespace']}_"
            f"{row['Resource Type']}_{row['Workload']}_"
            f"{row['Container']}"
        )
        local_selected = set(st.session_state.get(local_key, []))
        local_selected &= set(available_changes)
        st.session_state[local_key] = sorted(local_selected)

        title = (
            f"🟠 NORMAL | {row['Resource Type']} | {row['Namespace']} | "
            f"{row['Workload']} | {row['Container']}"
        )

        with st.expander(title, expanded=True):
            st.caption(
                f"{row['Resource Type']}: CPU/Memory comparison | "
                f"{len(available_changes)} selectable difference(s)."
            )

            display_rows = []
            for field in RESOURCE_FIELDS:
                status = row.get(f"{field} Status", "Not Found")
                display_rows.append({
                    "Select": field in local_selected,
                    "Resource": field,
                    "Source Value": row.get(f"Source {field}", "-"),
                    "Destination Value": row.get(f"Destination {field}", "-"),
                    "Status": status,
                })

            editor_df = pd.DataFrame(display_rows)
            editor_key = (
                f"cm_editor_{row['Namespace']}_{row['Resource Type']}_"
                f"{row['Workload']}_{row['Container']}_"
                f"{st.session_state.cm_global_revision}"
            )

            edited = st.data_editor(
                editor_df,
                key=editor_key,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                disabled=[
                    "Resource",
                    "Source Value",
                    "Destination Value",
                    "Status",
                ],
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select this resource change for Global Update.",
                        default=False,
                    ),
                    "Resource": st.column_config.TextColumn("Resource"),
                    "Source Value": st.column_config.TextColumn(
                        f"{source_env} Value"
                    ),
                    "Destination Value": st.column_config.TextColumn(
                        f"{destination_env} Value"
                    ),
                    "Status": st.column_config.TextColumn("Status"),
                },
            )

            edited_df = editor_df.copy()
            if isinstance(edited, dict) and "edited_rows" in edited:
                for row_index, changes in edited.get("edited_rows", {}).items():
                    if row_index < len(edited_df):
                        for column, value in changes.items():
                            if column in edited_df.columns:
                                edited_df.at[row_index, column] = value
            elif isinstance(edited, pd.DataFrame):
                edited_df = edited.copy()

            current_selected = {
                str(item["Resource"])
                for _, item in edited_df.iterrows()
                if bool(item.get("Select", False))
                and str(item["Resource"]) in available_changes
            }
            st.session_state[local_key] = sorted(current_selected)

            st.caption(
                f"Currently selected in this table: "
                f"{len(current_selected)} change(s)."
            )

            add_col, clear_col = st.columns([3, 1])
            with add_col:
                add_global = st.button(
                    f"➕ Add {len(current_selected)} Selected Changes to Global Update",
                    type="primary",
                    use_container_width=True,
                    disabled=not current_selected,
                    key=(
                        f"cm_add_global_{item_index}_"
                        f"{st.session_state.cm_global_revision}"
                    ),
                )
            with clear_col:
                clear_table = st.button(
                    "🗑️ Clear Table",
                    use_container_width=True,
                    disabled=not current_selected,
                    key=(
                        f"cm_clear_table_{item_index}_"
                        f"{st.session_state.cm_global_revision}"
                    ),
                )

            if add_global:
                queue = st.session_state.cm_global_selected
                for change_type in sorted(current_selected):
                    queue_key = (
                        row["Resource Type"],
                        row["Namespace"],
                        row["Workload"],
                        row["Container"],
                        change_type,
                    )
                    entry = {
                        "Resource Type": row["Resource Type"],
                        "Namespace": row["Namespace"],
                        "Workload": row["Workload"],
                        "Container": row["Container"],
                        "Change": change_type,
                        "Source Value": row.get(f"Source {change_type}", "-"),
                        "Destination Value": row.get(f"Destination {change_type}", "-"),
                        "Status": row.get(f"{change_type} Status", ""),
                        "_key": queue_key,
                    }
                    for q_index, existing in enumerate(queue):
                        if existing.get("_key") == queue_key:
                            queue[q_index] = entry
                            break
                    else:
                        queue.append(entry)

                st.session_state.cm_global_selected = queue
                st.session_state.cm_global_revision += 1
                st.rerun()

            if clear_table:
                st.session_state[local_key] = []
                st.session_state.cm_global_revision += 1
                st.rerun()

    # ========================================================
    # GLOBAL UPDATE QUEUE + CONFIRMATION
    # ========================================================

    queue = st.session_state.get("cm_global_selected", [])
    if not queue:
        return

    st.divider()
    st.markdown(
        f"## 🚀 Global Update Destination ({source_env} → {destination_env})"
    )
    st.success(
        f"{len(queue)} selected change(s) are queued for {destination_env}."
    )
    st.info(
        "Review the list. Only rows checked in the Update column will be applied. "
        "Unselected resource fields remain unchanged."
    )

    queue_df = pd.DataFrame(queue)
    if "_key" in queue_df.columns:
        queue_df = queue_df.drop(columns=["_key"])
    if "Update" not in queue_df.columns:
        queue_df.insert(0, "Update", True)

    queue_editor_key = (
        f"cm_global_editor_{st.session_state.cm_global_revision}"
    )
    edited_queue = st.data_editor(
        queue_df,
        key=queue_editor_key,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Update": st.column_config.CheckboxColumn("Update", default=True),
            "Resource Type": st.column_config.TextColumn("Resource Type"),
            "Namespace": st.column_config.TextColumn("Namespace"),
            "Workload": st.column_config.TextColumn("Workload"),
            "Container": st.column_config.TextColumn("Container"),
            "Change": st.column_config.TextColumn("Change"),
            "Source Value": st.column_config.TextColumn(source_env),
            "Destination Value": st.column_config.TextColumn(destination_env),
            "Status": st.column_config.TextColumn("Status"),
        },
        disabled=[
            "Resource Type", "Namespace", "Workload", "Container",
            "Change", "Source Value", "Destination Value", "Status",
        ],
    )

    final_queue = queue_df.copy()
    if isinstance(edited_queue, dict) and "edited_rows" in edited_queue:
        for row_index, changes in edited_queue.get("edited_rows", {}).items():
            if row_index < len(final_queue):
                for column, value in changes.items():
                    if column in final_queue.columns:
                        final_queue.at[row_index, column] = value
    elif isinstance(edited_queue, pd.DataFrame):
        final_queue = edited_queue.copy()

    checked_count = int(final_queue["Update"].fillna(False).astype(bool).sum())
    st.caption(
        f"{checked_count} change(s) currently selected for the final "
        f"{destination_env} update."
    )

    remove_col, clear_col = st.columns(2)
    with remove_col:
        if st.button(
            "🗑️ Remove Unticked Changes",
            use_container_width=True,
            key="cm_remove_unticked_v5",
        ):
            st.session_state.cm_global_selected = [
                queue[i] for i in final_queue.index
                if bool(final_queue.at[i, "Update"])
                and i < len(queue)
            ]
            st.session_state.cm_global_revision += 1
            st.rerun()
    with clear_col:
        if st.button(
            "🧹 Clear Global Update Queue",
            use_container_width=True,
            key="cm_clear_global_queue_v5",
        ):
            st.session_state.cm_global_selected = []
            st.session_state.cm_global_revision += 1
            st.session_state.cm_pending_update = False
            st.rerun()

    if checked_count == 0:
        st.warning("No changes are selected for update. Tick at least one row to continue.")
        return

    st.markdown(
        f"""
        <div class="cm-warning">
        <b>⚠️ Confirm {destination_env} Update</b><br><br>
        The checked changes will copy the selected values from
        <b>{source_env}</b> to <b>{destination_env}</b>.<br>
        Only the selected resource field is modified.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        f"🚀 Review & Confirm Update to {destination_env}",
        type="primary",
        use_container_width=True,
        key="cm_apply_selected_v5",
    ):
        st.session_state.cm_pending_update = True
        st.rerun()

    if st.session_state.get("cm_pending_update", False):
        st.warning(
            f"⚠️ FINAL CONFIRMATION: {checked_count} selected change(s) "
            f"will be applied to {destination_env}."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            confirm_update = st.button(
                f"✅ Confirm & Update {destination_env}",
                type="primary",
                use_container_width=True,
                key="cm_confirm_update_v5",
            )
        with cancel_col:
            cancel_update = st.button(
                "❌ Cancel",
                use_container_width=True,
                key="cm_cancel_update_v5",
            )

        if cancel_update:
            st.session_state.cm_pending_update = False
            st.rerun()

        if confirm_update:
            st.session_state.cm_pending_update = False
            success_count = 0
            failed_count = 0
            messages = []
            progress = st.progress(0)

            # Group selected changes by workload/container.
            # Before this optimization, 4 selected fields caused 4 GET +
            # 4 PATCH calls. Now they become 1 GET + 1 PATCH.
            grouped_updates = {}

            for queue_index in final_queue.index:
                if not bool(final_queue.at[queue_index, "Update"]):
                    continue

                queue_row = queue[queue_index]
                group_key = (
                    queue_row["Resource Type"],
                    queue_row["Namespace"],
                    queue_row["Workload"],
                    queue_row["Container"],
                )

                grouped_updates.setdefault(group_key, []).append(queue_row)

            total_workloads = len(grouped_updates)

            for position, (group_key, change_rows) in enumerate(
                grouped_updates.items()
            ):
                resource_type, namespace, workload_name, container_name = group_key

                kwargs = {
                    "cpu_request": None,
                    "memory_request": None,
                    "cpu_limit": None,
                    "memory_limit": None,
                }

                valid_changes = []

                for queue_row in change_rows:
                    change_type = queue_row["Change"]
                    value = queue_row["Source Value"]

                    if change_type == "CPU Request":
                        kwargs["cpu_request"] = value
                    elif change_type == "Memory Request":
                        kwargs["memory_request"] = value
                    elif change_type == "CPU Limit":
                        kwargs["cpu_limit"] = value
                    elif change_type == "Memory Limit":
                        kwargs["memory_limit"] = value
                    else:
                        failed_count += 1
                        messages.append(
                            f"Unknown change type: {change_type}"
                        )
                        continue

                    valid_changes.append((queue_row, change_type, value))

                if not valid_changes:
                    progress.progress(
                        (position + 1) / max(1, total_workloads)
                    )
                    continue

                try:
                    update_workload(
                        api_client=destination_client,
                        namespace=namespace,
                        resource_type=resource_type,
                        workload_name=workload_name,
                        container_name=container_name,
                        **kwargs,
                    )

                    # One Kubernetes PATCH can apply all selected fields
                    # for this workload/container.
                    success_count += len(valid_changes)

                    for queue_row, change_type, value in valid_changes:
                        messages.append(
                            f"Updated {queue_row['Resource Type']}/"
                            f"{queue_row['Workload']}/"
                            f"{queue_row['Container']} {change_type}: "
                            f"{queue_row['Destination Value']} → {value}"
                        )

                except Exception as exc:
                    failed_count += len(valid_changes)
                    messages.append(
                        f"Failed {resource_type}/{workload_name}/"
                        f"{container_name} for "
                        f"{len(valid_changes)} selected change(s): {exc}"
                    )

                progress.progress(
                    (position + 1) / max(1, total_workloads)
                )

            if failed_count == 0:
                st.success(
                    f"✅ Successfully updated {success_count} change(s) in "
                    f"{destination_env}."
                )
                st.session_state.cm_global_selected = []
                st.session_state.cm_global_revision += 1
            else:
                st.warning(
                    f"Completed with {success_count} successful and "
                    f"{failed_count} failed change(s)."
                )

            if messages:
                with st.expander("Update Details", expanded=False):
                    for message in messages:
                        st.write(message)

            st.info(
                f"Run 'Extract {source_env} → {destination_env}' again "
                f"to verify the destination values."
            )