import json
import os
import subprocess
import tempfile
from typing import Dict, List, Tuple

import streamlit as st


# ============================================================
# ENVIRONMENTS
# ============================================================

ENVIRONMENTS = [
    "DEV",
    "UAT",
    "STAGING",
    "PREPROD",
    "PROD",
    "BLUE",
    "GREEN",
]


# ============================================================
# SUPPORTED KUBERNETES WORKLOADS
# ============================================================

WORKLOAD_KINDS = [
    "deployment",
    "statefulset",
    "daemonset",
    "job",
    "cronjob",
]


# ============================================================
# PAGE CSS
# ============================================================

def render_styles():

    st.markdown(
        """
        <style>

        .image-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
        }

        .image-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 25px;
        }

        .direction-box {
            background: #eef5ff;
            border: 1px solid #cbdcf7;
            border-radius: 10px;
            padding: 18px 22px;
            margin: 18px 0 28px 0;
            font-size: 17px;
            font-weight: 600;
            color: #17345f;
        }

        .source-env {
            color: #137333;
            font-weight: 700;
        }

        .target-env {
            color: #b42318;
            font-weight: 700;
        }

        .summary-card {
            padding: 10px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SESSION STATE
# ============================================================

def initialize_session_state():

    if "image_source_env" not in st.session_state:
        st.session_state.image_source_env = "GREEN"

    if "image_target_env" not in st.session_state:
        st.session_state.image_target_env = "BLUE"

    if "image_compare_namespace" not in st.session_state:
        st.session_state.image_compare_namespace = None

    if "image_compare_results" not in st.session_state:
        st.session_state.image_compare_results = []

    if "image_compare_loaded" not in st.session_state:
        st.session_state.image_compare_loaded = False


# ============================================================
# SWAP SOURCE / TARGET
# ============================================================

def swap_source_target():

    source = st.session_state.image_source_env
    target = st.session_state.image_target_env

    st.session_state.image_source_env = target
    st.session_state.image_target_env = source

    # Old comparison is no longer valid.
    st.session_state.image_compare_results = []
    st.session_state.image_compare_loaded = False
    st.session_state.image_compare_namespace = None


# ============================================================
# RUN KUBECTL
# ============================================================

def run_kubectl(
    kubeconfig: str,
    args: List[str],
    timeout: int = 120,
) -> Tuple[bool, str]:

    command = [
        "kubectl",
        "--kubeconfig",
        kubeconfig,
    ]

    command.extend(args)

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:

            return (
                False,
                stderr or stdout or "kubectl command failed",
            )

        return True, stdout

    except FileNotFoundError:

        return (
            False,
            "kubectl was not found in PATH. "
            "Install kubectl and make sure it is available from PowerShell.",
        )

    except subprocess.TimeoutExpired:

        return (
            False,
            f"kubectl command timed out after {timeout} seconds.",
        )

    except Exception as exc:

        return False, str(exc)


# ============================================================
# SAVE KUBECONFIG
# ============================================================

def save_kubeconfig(
    uploaded_file,
    environment: str,
) -> str:

    temp_directory = os.path.join(
        tempfile.gettempdir(),
        "si_platform_image_comparator",
    )

    os.makedirs(
        temp_directory,
        exist_ok=True,
    )

    safe_environment = "".join(
        character
        if character.isalnum() or character in ("-", "_")
        else "_"
        for character in environment
    )

    path = os.path.join(
        temp_directory,
        f"{safe_environment}_kubeconfig.yaml",
    )

    with open(path, "wb") as file:

        file.write(
            uploaded_file.getvalue()
        )

    return path


# ============================================================
# CLUSTER CONNECTIVITY
# ============================================================

def check_cluster_connection(
    kubeconfig: str,
) -> Tuple[bool, str]:

    # IMPORTANT:
    #
    # Do NOT use:
    #
    # kubectl version --short
    #
    # because some kubectl versions do not support --short.
    #
    # cluster-info works with old/new kubectl versions and
    # is suitable for RKE1/RKE2.

    ok, output = run_kubectl(
        kubeconfig,
        [
            "cluster-info",
        ],
        timeout=30,
    )

    if ok:

        return True, output

    # Fallback

    ok, output = run_kubectl(
        kubeconfig,
        [
            "version",
            "-o",
            "json",
        ],
        timeout=30,
    )

    if ok:

        return True, output

    return False, output


# ============================================================
# GET KUBERNETES NAMESPACES
# ============================================================

def get_namespaces(
    kubeconfig: str,
) -> Tuple[List[str], str]:

    ok, output = run_kubectl(
        kubeconfig,
        [
            "get",
            "namespaces",
            "-o",
            "json",
        ],
    )

    if not ok:

        return [], output

    try:

        data = json.loads(output)

    except json.JSONDecodeError:

        return [], "Unable to parse namespace JSON."

    namespaces = []

    for item in data.get("items", []):

        name = (
            item
            .get("metadata", {})
            .get("name")
        )

        if name:

            namespaces.append(name)

    return sorted(namespaces), ""


# ============================================================
# GET WORKLOADS
# ============================================================

def get_workloads(
    kubeconfig: str,
    namespace: str,
) -> Tuple[List[Dict], List[str]]:

    workloads = []
    errors = []

    for kind in WORKLOAD_KINDS:

        ok, output = run_kubectl(
            kubeconfig,
            [
                "get",
                kind,
                "-n",
                namespace,
                "-o",
                "json",
            ],
        )

        if not ok:

            errors.append(
                f"{kind}: {output}"
            )

            continue

        try:

            data = json.loads(output)

        except json.JSONDecodeError:

            errors.append(
                f"{kind}: invalid JSON returned by kubectl."
            )

            continue

        for item in data.get("items", []):

            metadata = item.get(
                "metadata",
                {},
            )

            workload_name = metadata.get(
                "name"
            )

            if not workload_name:
                continue

            # ------------------------------------------------
            # POD TEMPLATE
            # ------------------------------------------------

            if kind == "cronjob":

                template = (
                    item
                    .get("spec", {})
                    .get("jobTemplate", {})
                    .get("spec", {})
                    .get("template", {})
                )

            else:

                template = (
                    item
                    .get("spec", {})
                    .get("template", {})
                )

            pod_spec = template.get(
                "spec",
                {},
            )

            containers = []

            # ------------------------------------------------
            # NORMAL CONTAINERS
            # ------------------------------------------------

            for container in pod_spec.get(
                "containers",
                [],
            ):

                containers.append(
                    {
                        "name": container.get(
                            "name",
                            "",
                        ),
                        "image": container.get(
                            "image",
                            "",
                        ),
                    }
                )

            # ------------------------------------------------
            # INIT CONTAINERS
            # ------------------------------------------------

            for container in pod_spec.get(
                "initContainers",
                [],
            ):

                containers.append(
                    {
                        "name": container.get(
                            "name",
                            "",
                        ),
                        "image": container.get(
                            "image",
                            "",
                        ),
                    }
                )

            workloads.append(
                {
                    "kind": kind,
                    "name": workload_name,
                    "namespace": namespace,
                    "containers": containers,
                }
            )

    return workloads, errors


# ============================================================
# BUILD WORKLOAD MAP
# ============================================================

def build_workload_map(
    workloads: List[Dict],
) -> Dict:

    result = {}

    for workload in workloads:

        key = (
            workload["kind"],
            workload["name"],
        )

        result[key] = workload

    return result


# ============================================================
# COMPARE IMAGES
# ============================================================

def compare_images(
    source_workloads: List[Dict],
    target_workloads: List[Dict],
) -> List[Dict]:

    source_map = build_workload_map(
        source_workloads
    )

    target_map = build_workload_map(
        target_workloads
    )

    all_workloads = sorted(
        set(source_map.keys())
        |
        set(target_map.keys())
    )

    results = []

    for kind, workload_name in all_workloads:

        source_workload = source_map.get(
            (kind, workload_name)
        )

        target_workload = target_map.get(
            (kind, workload_name)
        )

        source_containers = {}

        target_containers = {}

        if source_workload:

            source_containers = {
                container["name"]:
                    container["image"]
                for container
                in source_workload["containers"]
                if container["name"]
            }

        if target_workload:

            target_containers = {
                container["name"]:
                    container["image"]
                for container
                in target_workload["containers"]
                if container["name"]
            }

        all_containers = sorted(
            set(source_containers.keys())
            |
            set(target_containers.keys())
        )

        for container_name in all_containers:

            source_image = (
                source_containers.get(
                    container_name
                )
            )

            target_image = (
                target_containers.get(
                    container_name
                )
            )

            # ----------------------------------------------
            # STATUS
            # ----------------------------------------------

            if source_image is None:

                status = "SOURCE MISSING"

            elif target_image is None:

                status = "TARGET MISSING"

            elif source_image == target_image:

                status = "SAME"

            else:

                status = "DIFFERENT"

            results.append(
                {
                    "kind": kind,
                    "workload": workload_name,
                    "container": container_name,
                    "source_image": source_image or "-",
                    "target_image": target_image or "-",
                    "status": status,
                }
            )

    return results


# ============================================================
# UPDATE TARGET IMAGE
# ============================================================

def update_target_image(
    kubeconfig: str,
    namespace: str,
    kind: str,
    workload: str,
    container: str,
    source_image: str,
) -> Tuple[bool, str]:

    if not source_image or source_image == "-":

        return (
            False,
            "Source image is missing.",
        )

    # --------------------------------------------------------
    # CRONJOB
    # --------------------------------------------------------

    if kind == "cronjob":

        ok, output = run_kubectl(
            kubeconfig,
            [
                "set",
                "image",
                f"cronjob/{workload}",
                f"{container}={source_image}",
                "-n",
                namespace,
            ],
        )

        return ok, output

    # --------------------------------------------------------
    # STANDARD WORKLOADS
    # --------------------------------------------------------

    supported = [
        "deployment",
        "statefulset",
        "daemonset",
        "job",
    ]

    if kind not in supported:

        return (
            False,
            f"Unsupported workload type: {kind}",
        )

    ok, output = run_kubectl(
        kubeconfig,
        [
            "set",
            "image",
            f"{kind}/{workload}",
            f"{container}={source_image}",
            "-n",
            namespace,
        ],
    )

    return ok, output


# ============================================================
# RENDER DIFFERENCE TABLE
# ============================================================

def render_selected_table(
    differences: List[Dict],
    selected_indexes: List[int],
    source_environment: str,
    target_environment: str,
):

    rows = []

    for index in selected_indexes:

        item = differences[index]

        rows.append(
            {
                "Workload Type":
                    item["kind"].upper(),

                "Workload":
                    item["workload"],

                "Container":
                    item["container"],

                source_environment:
                    item["source_image"],

                target_environment:
                    item["target_image"],

                "Action":
                    f"UPDATE {target_environment}",
            }
        )

    if rows:

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Select one or more different images."
        )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_image_comparator():

    initialize_session_state()

    render_styles()

    # ========================================================
    # TITLE
    # ========================================================

    st.html(
        """
        <div style="margin-bottom:5px;">

            <span style="
                font-size:42px;
                vertical-align:middle;
            ">
                🐳
            </span>

            <span style="
                font-size:36px;
                font-weight:700;
                color:#18213d;
                vertical-align:middle;
                margin-left:8px;
            ">
                Image Comparator
            </span>

        </div>
        """
    )

    st.markdown(
        """
        <div class="image-subtitle">
            Compare Kubernetes container images between two environments
            and safely update the target environment.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # SOURCE / TARGET
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        source_environment = st.selectbox(
            "Select Source Environment",
            ENVIRONMENTS,
            key="image_source_env",
        )

    with col2:

        target_environment = st.selectbox(
            "Select Target Environment",
            ENVIRONMENTS,
            key="image_target_env",
        )

    # ========================================================
    # SWAP
    # ========================================================

    st.button(
        "🔄  Swap Source & Target",
        key="image_swap_button",
        on_click=swap_source_target,
    )

    # ========================================================
    # TRANSFER DIRECTION
    # ========================================================

    st.html(
        f"""
        <div class="direction-box">

            Transfer Direction:

            <span class="source-env"
                  style="padding-left:10px;">
                {source_environment}
            </span>

            <span style="
                padding:0 14px;
                color:#667085;
                font-size:22px;
            ">
                →
            </span>

            <span class="target-env">
                {target_environment}
            </span>

        </div>
        """
    )

    # ========================================================
    # SAME ENVIRONMENT VALIDATION
    # ========================================================

    if source_environment == target_environment:

        st.error(
            "Source and target environments cannot be the same."
        )

        return

    # ========================================================
    # KUBECONFIG UPLOAD
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            f"Environment 1 — {source_environment}"
        )

        source_file = st.file_uploader(
            f"Upload {source_environment} kubeconfig",
            type=[
                "yaml",
                "yml",
                "conf",
            ],
            key="image_source_kubeconfig_upload",
        )

        if source_file:

            st.success(
                f"{source_environment} kubeconfig loaded: "
                f"{source_file.name}"
            )

    with col2:

        st.subheader(
            f"Environment 2 — {target_environment}"
        )

        target_file = st.file_uploader(
            f"Upload {target_environment} kubeconfig",
            type=[
                "yaml",
                "yml",
                "conf",
            ],
            key="image_target_kubeconfig_upload",
        )

        if target_file:

            st.success(
                f"{target_environment} kubeconfig loaded: "
                f"{target_file.name}"
            )

    # ========================================================
    # WAIT FOR BOTH
    # ========================================================

    if source_file is None:

        st.info(
            f"Upload the {source_environment} kubeconfig."
        )

        return

    if target_file is None:

        st.info(
            f"Upload the {target_environment} kubeconfig."
        )

        return

    # ========================================================
    # SAVE FILES
    # ========================================================

    source_kubeconfig = save_kubeconfig(
        source_file,
        source_environment,
    )

    target_kubeconfig = save_kubeconfig(
        target_file,
        target_environment,
    )

    # ========================================================
    # CONNECTIVITY CHECK
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        source_connected, source_message = (
            check_cluster_connection(
                source_kubeconfig
            )
        )

        if source_connected:

            st.success(
                f"{source_environment} cluster connected successfully."
            )

        else:

            st.error(
                f"Unable to connect to "
                f"{source_environment}: "
                f"{source_message}"
            )

    with col2:

        target_connected, target_message = (
            check_cluster_connection(
                target_kubeconfig
            )
        )

        if target_connected:

            st.success(
                f"{target_environment} cluster connected successfully."
            )

        else:

            st.error(
                f"Unable to connect to "
                f"{target_environment}: "
                f"{target_message}"
            )

    if not source_connected or not target_connected:

        return

    # ========================================================
    # NAMESPACE DISCOVERY
    # ========================================================

    source_namespaces, source_namespace_error = (
        get_namespaces(
            source_kubeconfig
        )
    )

    target_namespaces, target_namespace_error = (
        get_namespaces(
            target_kubeconfig
        )
    )

    if source_namespace_error:

        st.error(
            f"Unable to read {source_environment} namespaces: "
            f"{source_namespace_error}"
        )

        return

    if target_namespace_error:

        st.error(
            f"Unable to read {target_environment} namespaces: "
            f"{target_namespace_error}"
        )

        return

    # ========================================================
    # COMMON NAMESPACES
    # ========================================================

    common_namespaces = sorted(
        set(source_namespaces)
        &
        set(target_namespaces)
    )

    if not common_namespaces:

        st.warning(
            "No common namespaces were found between "
            f"{source_environment} and "
            f"{target_environment}."
        )

        return

    # ========================================================
    # NAMESPACE
    # ========================================================

    namespace = st.selectbox(
        "Namespace to compare",
        common_namespaces,
        key="image_compare_namespace_select",
    )

    # ========================================================
    # LOAD / COMPARE
    # ========================================================

    if st.button(
        "🔍  Compare Images",
        key="image_compare_button",
        use_container_width=True,
        type="primary",
    ):

        with st.spinner(
            f"Reading workloads from "
            f"{source_environment} and "
            f"{target_environment}..."
        ):

            source_workloads, source_errors = (
                get_workloads(
                    source_kubeconfig,
                    namespace,
                )
            )

            target_workloads, target_errors = (
                get_workloads(
                    target_kubeconfig,
                    namespace,
                )
            )

            results = compare_images(
                source_workloads,
                target_workloads,
            )

        st.session_state.image_compare_results = (
            results
        )

        st.session_state.image_compare_loaded = True

        st.session_state.image_compare_namespace = (
            namespace
        )

        # ----------------------------------------------------
        # Discovery warnings
        # ----------------------------------------------------

        if source_errors:

            with st.expander(
                f"{source_environment} discovery messages"
            ):

                for error in source_errors:

                    st.warning(error)

        if target_errors:

            with st.expander(
                f"{target_environment} discovery messages"
            ):

                for error in target_errors:

                    st.warning(error)

    # ========================================================
    # RESULTS
    # ========================================================

    if not st.session_state.image_compare_loaded:

        return

    results = (
        st.session_state.image_compare_results
    )

    if not results:

        st.info(
            "No workloads or containers found "
            "in the selected namespace."
        )

        return

    # ========================================================
    # SUMMARY
    # ========================================================

    same_count = sum(
        1
        for item in results
        if item["status"] == "SAME"
    )

    different_count = sum(
        1
        for item in results
        if item["status"] == "DIFFERENT"
    )

    missing_count = sum(
        1
        for item in results
        if item["status"] in [
            "SOURCE MISSING",
            "TARGET MISSING",
        ]
    )

    total_count = len(results)

    st.divider()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Containers",
        total_count,
    )

    c2.metric(
        "Same",
        same_count,
    )

    c3.metric(
        "Different",
        different_count,
    )

    c4.metric(
        "Missing",
        missing_count,
    )

    # ========================================================
    # DIFFERENCES
    # ========================================================

    differences = [
        item
        for item in results
        if item["status"] == "DIFFERENT"
    ]

    st.divider()

    st.subheader(
        "🔄 Image Differences"
    )

    st.caption(
        f"Source: {source_environment} → "
        f"Target: {target_environment} | "
        f"Namespace: {namespace}"
    )

    if not differences:

        st.success(
            "All available container images are the same."
        )

    else:

        # ====================================================
        # SELECT ALL
        # ====================================================

        select_all = st.checkbox(
            "Select all different images",
            key="image_select_all",
        )

        selected_indexes = []

        # ====================================================
        # DIFFERENCE CHECKBOXES
        # ====================================================

        for index, item in enumerate(
            differences
        ):

            label = (
                f"{item['kind'].upper()} / "
                f"{item['workload']} / "
                f"{item['container']}"
            )

            selected = st.checkbox(
                label,
                value=select_all,
                key=f"image_difference_{index}",
            )

            if selected:

                selected_indexes.append(
                    index
                )

        # ====================================================
        # LAST TABLE
        # ====================================================

        st.subheader(
            "Selected Image Changes"
        )

        render_selected_table(
            differences=differences,
            selected_indexes=selected_indexes,
            source_environment=source_environment,
            target_environment=target_environment,
        )

        # ====================================================
        # UPDATE
        # ====================================================

        if selected_indexes:

            st.warning(
                f"{len(selected_indexes)} image(s) "
                f"will be updated in "
                f"{target_environment}."
            )

            if st.button(
                f"🚀 Update Selected Images in "
                f"{target_environment}",
                key="image_update_button",
                use_container_width=True,
                type="primary",
            ):

                progress = st.progress(
                    0
                )

                status_message = st.empty()

                success_count = 0
                failed_count = 0

                update_results = []

                total_updates = len(
                    selected_indexes
                )

                # ============================================
                # UPDATE EACH IMAGE
                # ============================================

                for position, index in enumerate(
                    selected_indexes,
                    start=1,
                ):

                    item = differences[
                        index
                    ]

                    status_message.info(
                        "Updating "
                        f"{item['kind']}/"
                        f"{item['workload']} "
                        f"→ {item['source_image']}"
                    )

                    ok, message = (
                        update_target_image(
                            kubeconfig=target_kubeconfig,
                            namespace=namespace,
                            kind=item["kind"],
                            workload=item["workload"],
                            container=item["container"],
                            source_image=item["source_image"],
                        )
                    )

                    if ok:

                        success_count += 1

                        update_results.append(
                            {
                                "Workload":
                                    item["workload"],

                                "Container":
                                    item["container"],

                                "Source Image":
                                    item["source_image"],

                                "Status":
                                    "UPDATED",

                                "Message":
                                    message,
                            }
                        )

                    else:

                        failed_count += 1

                        update_results.append(
                            {
                                "Workload":
                                    item["workload"],

                                "Container":
                                    item["container"],

                                "Source Image":
                                    item["source_image"],

                                "Status":
                                    "FAILED",

                                "Message":
                                    message,
                            }
                        )

                    progress.progress(
                        position / total_updates
                    )

                status_message.empty()

                # ============================================
                # UPDATE SUMMARY
                # ============================================

                st.divider()

                if success_count:

                    st.success(
                        f"{success_count} image(s) "
                        f"updated successfully in "
                        f"{target_environment}."
                    )

                if failed_count:

                    st.error(
                        f"{failed_count} image(s) "
                        f"failed to update."
                    )

                st.dataframe(
                    update_results,
                    use_container_width=True,
                    hide_index=True,
                )

                st.info(
                    "Click Compare Images again to verify "
                    "the target environment."
                )

    # ========================================================
    # COMPLETE LAST TABLE
    # ========================================================

    st.divider()

    st.subheader(
        "📋 Image Comparison"
    )

    final_rows = []

    for item in results:

        final_rows.append(
            {
                "Workload Type":
                    item["kind"].upper(),

                "Workload":
                    item["workload"],

                "Container":
                    item["container"],

                source_environment:
                    item["source_image"],

                target_environment:
                    item["target_image"],

                "Status":
                    item["status"],
            }
        )

    st.dataframe(
        final_rows,
        use_container_width=True,
        hide_index=True,
    )