import streamlit as st
import tempfile
import os
import io
import pandas as pd

from kubernetes import client, config


# ============================================================
# LOAD KUBECONFIG
# ============================================================

def load_kubeconfig(uploaded_file):

    kubeconfig_content = uploaded_file.getvalue()

    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        suffix=".yaml",
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
# ANALYZE POD PROBLEM
# ============================================================

def analyze_container_problem(
    pod_phase,
    container_state,
    reason,
    message,
    restart_count,
):

    reason_lower = (
        str(reason or "")
        .lower()
    )

    message_lower = (
        str(message or "")
        .lower()
    )

    state_lower = (
        str(container_state or "")
        .lower()
    )


    # --------------------------------------------------------
    # CrashLoopBackOff
    # --------------------------------------------------------

    if "crashloopbackoff" in reason_lower:

        return (
            "🔴 High Priority",
            "Container is repeatedly crashing and Kubernetes "
            "is restarting it.",
            "Check application logs, previous container logs, "
            "environment variables, configuration and dependencies.",
            "kubectl logs <pod> -n <namespace> --previous",
        )


    # --------------------------------------------------------
    # ImagePullBackOff
    # --------------------------------------------------------

    if (
        "imagepullbackoff" in reason_lower
        or "errimagepull" in reason_lower
    ):

        return (
            "🔴 High Priority",
            "Kubernetes cannot pull the container image.",
            "Check image name/tag, registry connectivity, "
            "imagePullSecrets and registry authentication.",
            "kubectl describe pod <pod> -n <namespace>",
        )


    # --------------------------------------------------------
    # CreateContainerConfigError
    # --------------------------------------------------------

    if (
        "createcontainerconfigerror"
        in reason_lower
    ):

        return (
            "🔴 High Priority",
            "Container configuration could not be created.",
            "Check ConfigMaps, Secrets, environment variables, "
            "volume references and service-account configuration.",
            "kubectl describe pod <pod> -n <namespace>",
        )


    # --------------------------------------------------------
    # CreateContainerError
    # --------------------------------------------------------

    if "createcontainererror" in reason_lower:

        return (
            "🔴 High Priority",
            "Kubernetes failed while creating the container.",
            "Check volume mounts, permissions, container command, "
            "runtime configuration and pod events.",
            "kubectl describe pod <pod> -n <namespace>",
        )


    # --------------------------------------------------------
    # ContainerCreating
    # --------------------------------------------------------

    if (
        "containercreating" in reason_lower
        or "containercreating" in state_lower
    ):

        return (
            "🟠 Medium Priority",
            "Container is taking longer than expected to start.",
            "Check image pulling, volume mounting, CNI/networking "
            "and Kubernetes events.",
            "kubectl describe pod <pod> -n <namespace>",
        )


    # --------------------------------------------------------
    # Pending
    # --------------------------------------------------------

    if pod_phase.lower() == "pending":

        return (
            "🟠 Medium Priority",
            "Pod has not been scheduled or started successfully.",
            "Check node resources, node selectors, taints, "
            "affinity rules, PVCs and scheduling events.",
            "kubectl describe pod <pod> -n <namespace>",
        )


    # --------------------------------------------------------
    # Terminating
    # --------------------------------------------------------

    if (
        "terminating" in reason_lower
        or "terminating" in message_lower
    ):

        return (
            "🟠 Medium Priority",
            "Pod is stuck while being deleted.",
            "Check finalizers, volume detach operations and "
            "node connectivity before considering force deletion.",
            "kubectl get pod <pod> -n <namespace> -o yaml",
        )


    # --------------------------------------------------------
    # Error
    # --------------------------------------------------------

    if (
        pod_phase.lower() == "failed"
        or reason_lower == "error"
        or "error" in reason_lower
    ):

        return (
            "🔴 High Priority",
            "Container or pod entered an error state.",
            "Check current and previous container logs and "
            "pod events to identify the failure.",
            "kubectl logs <pod> -n <namespace> --previous",
        )


    # --------------------------------------------------------
    # Generic
    # --------------------------------------------------------

    return (
        "🟡 Review",
        f"Container reported state: {reason or container_state}.",
        "Review pod events and container logs.",
        "kubectl describe pod <pod> -n <namespace>",
    )


# ============================================================
# SCAN PODS
# ============================================================

def scan_problem_pods(api_client):

    core_api = client.CoreV1Api(
        api_client
    )

    pods = core_api.list_pod_for_all_namespaces()

    rows = []


    for pod in pods.items:

        namespace = (
            pod.metadata.namespace
        )

        pod_name = (
            pod.metadata.name
        )

        pod_phase = (
            pod.status.phase
            if pod.status
            else "Unknown"
        )


        # ----------------------------------------------------
        # TERMINATING
        # ----------------------------------------------------

        terminating = (
            pod.metadata.deletion_timestamp
            is not None
        )


        # ----------------------------------------------------
        # POD CONTAINERS
        # ----------------------------------------------------

        container_statuses = []

        if pod.status:

            if pod.status.container_statuses:

                container_statuses.extend(
                    pod.status.container_statuses
                )

            if pod.status.init_container_statuses:

                container_statuses.extend(
                    pod.status.init_container_statuses
                )


        # ----------------------------------------------------
        # NORMAL CONTAINER STATUS
        # ----------------------------------------------------

        if container_statuses:

            for container_status in container_statuses:

                container_name = (
                    container_status.name
                )

                restart_count = (
                    container_status.restart_count
                )

                state_name = "Unknown"
                reason = ""
                message = ""


                # --------------------------------------------
                # WAITING
                # --------------------------------------------

                if container_status.state:

                    if container_status.state.waiting:

                        state_name = "Waiting"

                        reason = (
                            container_status
                            .state
                            .waiting
                            .reason
                            or ""
                        )

                        message = (
                            container_status
                            .state
                            .waiting
                            .message
                            or ""
                        )


                    # ----------------------------------------
                    # RUNNING
                    # ----------------------------------------

                    elif container_status.state.running:

                        state_name = "Running"


                    # ----------------------------------------
                    # TERMINATED
                    # ----------------------------------------

                    elif container_status.state.terminated:

                        state_name = "Terminated"

                        reason = (
                            container_status
                            .state
                            .terminated
                            .reason
                            or ""
                        )

                        message = (
                            container_status
                            .state
                            .terminated
                            .message
                            or ""
                        )


                # ------------------------------------------------
                # DETERMINE WHETHER THIS IS A PROBLEM
                # ------------------------------------------------

                is_problem = False

                if terminating:

                    is_problem = True

                elif pod_phase in [
                    "Pending",
                    "Failed",
                ]:

                    is_problem = True

                elif reason.lower() in [
                    "crashloopbackoff",
                    "imagepullbackoff",
                    "errimagepull",
                    "createcontainererror",
                    "createcontainerconfigerror",
                    "error",
                ]:

                    is_problem = True

                elif state_name in [
                    "Waiting",
                    "Terminated",
                ]:

                    is_problem = True


                if not is_problem:

                    continue


                display_reason = reason

                if terminating:

                    display_reason = (
                        "Terminating"
                    )


                severity, analysis, recommendation, command = (
                    analyze_container_problem(
                        pod_phase,
                        state_name,
                        display_reason,
                        message,
                        restart_count,
                    )
                )


                rows.append(
                    {
                        "Namespace": namespace,
                        "Pod": pod_name,
                        "Container": container_name,
                        "Pod Phase": pod_phase,
                        "Container State": state_name,
                        "Reason": display_reason,
                        "Restarts": restart_count,
                        "Severity": severity,
                        "AI Analysis": analysis,
                        "Recommendation": recommendation,
                        "Suggested Command": command,
                    }
                )


        # ----------------------------------------------------
        # POD WITHOUT CONTAINER STATUS
        # ----------------------------------------------------

        else:

            if (
                pod_phase in [
                    "Pending",
                    "Failed",
                ]
                or terminating
            ):

                reason = (
                    "Terminating"
                    if terminating
                    else pod_phase
                )


                severity, analysis, recommendation, command = (
                    analyze_container_problem(
                        pod_phase,
                        "",
                        reason,
                        "",
                        0,
                    )
                )


                rows.append(
                    {
                        "Namespace": namespace,
                        "Pod": pod_name,
                        "Container": "-",
                        "Pod Phase": pod_phase,
                        "Container State": "-",
                        "Reason": reason,
                        "Restarts": 0,
                        "Severity": severity,
                        "AI Analysis": analysis,
                        "Recommendation": recommendation,
                        "Suggested Command": command,
                    }
                )


    return pd.DataFrame(rows)


# ============================================================
# DELETE POD
# ============================================================

def delete_pod(
    api_client,
    namespace,
    pod_name,
):

    core_api = client.CoreV1Api(
        api_client
    )

    core_api.delete_namespaced_pod(
        name=pod_name,
        namespace=namespace,
        body=client.V1DeleteOptions(
            propagation_policy="Background"
        ),
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_container_status():

    st.markdown(
        """
        <style>

        .container-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
        }

        .container-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 24px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="container-title">'
        '🚦 Container Status'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="container-subtitle">'
        'Detect failed Kubernetes containers, analyze the '
        'likely cause and safely restart problematic pods.'
        '</div>',
        unsafe_allow_html=True,
    )


    # ========================================================
    # KUBECONFIG
    # ========================================================

    uploaded_file = st.file_uploader(
        "Upload kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf",
        ],
        key="container_status_kubeconfig",
    )


    if uploaded_file is None:

        st.info(
            "Upload a kubeconfig file to scan all namespaces."
        )

        return


    # ========================================================
    # CONNECT
    # ========================================================

    try:

        api_client = load_kubeconfig(
            uploaded_file
        )

        st.success(
            "Connected to Kubernetes cluster."
        )

    except Exception as exc:

        st.error(
            f"Failed to connect to Kubernetes cluster: {exc}"
        )

        return


    # ========================================================
    # SCAN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🔍 Container State Scan"
    )

    st.code(
        "kubectl get pods --all-namespaces | "
        "egrep 'Pending|ContainerCreating|error|Terminating'",
        language="bash",
    )


    if st.button(
        "🔍 Scan All Namespaces",
        use_container_width=True,
        type="primary",
        key="scan_container_status",
    ):

        try:

            with st.spinner(
                "Scanning Kubernetes pods..."
            ):

                df = scan_problem_pods(
                    api_client
                )


            st.session_state.container_status_df = df


        except Exception as exc:

            st.error(
                f"Failed to scan pods: {exc}"
            )

            return


    if (
        "container_status_df"
        not in st.session_state
    ):

        return


    df = (
        st.session_state
        .container_status_df
    )


    # ========================================================
    # NO PROBLEMS
    # ========================================================

    if df.empty:

        st.success(
            "✅ No failed or problematic container states found."
        )

        return


    # ========================================================
    # SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📊 Container Status Summary"
    )


    total = len(df)

    high = (
        df["Severity"]
        .str.contains(
            "High",
            na=False,
        )
        .sum()
    )

    medium = (
        df["Severity"]
        .str.contains(
            "Medium",
            na=False,
        )
        .sum()
    )

    terminating = (
        df["Reason"]
        .eq("Terminating")
        .sum()
    )


    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(
            "Problem Containers",
            total,
        )


    with c2:

        st.metric(
            "🔴 High Priority",
            high,
        )


    with c3:

        st.metric(
            "🟠 Medium",
            medium,
        )


    with c4:

        st.metric(
            "🗑️ Terminating",
            terminating,
        )


    # ========================================================
    # FILTER
    # ========================================================

    st.divider()

    col1, col2 = st.columns(2)


    with col1:

        namespace_filter = st.selectbox(
            "Namespace",
            [
                "All"
            ]
            + sorted(
                df["Namespace"]
                .unique()
                .tolist()
            ),
            key="container_namespace_filter",
        )


    with col2:

        state_filter = st.selectbox(
            "Container State",
            [
                "All"
            ]
            + sorted(
                df["Container State"]
                .unique()
                .tolist()
            ),
            key="container_state_filter",
        )


    filtered_df = df.copy()


    if namespace_filter != "All":

        filtered_df = filtered_df[
            filtered_df["Namespace"]
            == namespace_filter
        ]


    if state_filter != "All":

        filtered_df = filtered_df[
            filtered_df["Container State"]
            == state_filter
        ]


    # ========================================================
    # MAIN TABLE
    # ========================================================

    st.markdown(
        "### 🚨 Problematic Containers"
    )


    display_columns = [
        "Namespace",
        "Pod",
        "Container",
        "Pod Phase",
        "Container State",
        "Reason",
        "Restarts",
        "Severity",
    ]


    def color_severity(value):

        if "High" in str(value):

            return (
                "background-color:#fee2e2;"
                "color:#991b1b;"
                "font-weight:700;"
            )

        if "Medium" in str(value):

            return (
                "background-color:#fef3c7;"
                "color:#92400e;"
                "font-weight:700;"
            )

        return ""


    styled_df = (
        filtered_df[
            display_columns
        ]
        .style
        .map(
            color_severity,
            subset=["Severity"],
        )
    )


    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # AI ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 🤖 AI Analysis"
    )


    selected_key = st.selectbox(
        "Select a problematic container",
        [
            (
                f"{row['Namespace']} | "
                f"{row['Pod']} | "
                f"{row['Container']}"
            )
            for _, row
            in filtered_df.iterrows()
        ],
        key="selected_problem_container",
    )


    if selected_key:

        parts = selected_key.split(
            " | ",
            2,
        )


        selected_namespace = parts[0]
        selected_pod = parts[1]
        selected_container = parts[2]


        selected_row = filtered_df[
            (
                filtered_df["Namespace"]
                == selected_namespace
            )
            &
            (
                filtered_df["Pod"]
                == selected_pod
            )
            &
            (
                filtered_df["Container"]
                == selected_container
            )
        ].iloc[0]


        col1, col2 = st.columns(2)


        with col1:

            st.markdown(
                f"**Severity:** "
                f"{selected_row['Severity']}"
            )

            st.markdown(
                f"**Reason:** "
                f"`{selected_row['Reason']}`"
            )

            st.markdown(
                f"**Restarts:** "
                f"{selected_row['Restarts']}"
            )


        with col2:

            st.info(
                selected_row[
                    "AI Analysis"
                ]
            )


        st.markdown(
            "**Recommended Action**"
        )

        st.write(
            selected_row[
                "Recommendation"
            ]
        )


        st.markdown(
            "**Suggested Diagnostic Command**"
        )

        st.code(
            selected_row[
                "Suggested Command"
            ],
            language="bash",
        )


    # ========================================================
    # POD DELETE
    # ========================================================

    st.divider()

    st.markdown(
        "### 🗑️ Delete / Restart Pods"
    )

    st.warning(
        "Deleting a pod is a Kubernetes operation. "
        "For Deployments, StatefulSets and DaemonSets, "
        "the controller may automatically recreate the pod."
    )


    # Only one row per pod for deletion

    unique_pods = (
        filtered_df[
            [
                "Namespace",
                "Pod",
            ]
        ]
        .drop_duplicates()
    )


    pod_options = []

    for _, row in unique_pods.iterrows():

        pod_options.append(
            f"{row['Namespace']} | {row['Pod']}"
        )


    selected_pods = st.multiselect(
        "Select pods to delete",
        pod_options,
        key="pods_to_delete",
    )


    if selected_pods:

        st.markdown(
            "#### Selected Pods"
        )

        for pod in selected_pods:

            st.write(
                f"🗑️ {pod}"
            )


    confirm_delete = st.checkbox(
        "I understand that deleting these pods may "
        "restart the associated workloads.",
        key="confirm_pod_delete",
    )


    if st.button(
        "⚠️ Delete Selected Pods",
        use_container_width=True,
        type="primary",
        key="delete_selected_pods",
    ):

        if not selected_pods:

            st.error(
                "Please select at least one pod."
            )

        elif not confirm_delete:

            st.error(
                "Please confirm the deletion."
            )

        else:

            deleted = []
            failed = []


            for selected_pod in selected_pods:

                namespace, pod_name = (
                    selected_pod.split(
                        " | ",
                        1,
                    )
                )


                try:

                    delete_pod(
                        api_client,
                        namespace,
                        pod_name,
                    )

                    deleted.append(
                        selected_pod
                    )

                except Exception as exc:

                    failed.append(
                        {
                            "Pod":
                                selected_pod,
                            "Error":
                                str(exc),
                        }
                    )


            # ------------------------------------------------
            # RESULT
            # ------------------------------------------------

            if deleted:

                st.success(
                    f"Successfully deleted "
                    f"{len(deleted)} pod(s)."
                )


            if failed:

                st.error(
                    "Some pods could not be deleted."
                )

                st.dataframe(
                    pd.DataFrame(
                        failed
                    ),
                    use_container_width=True,
                    hide_index=True,
                )


            # Clear selection

            st.session_state.pods_to_delete = []


            # Refresh scan

            try:

                st.session_state.container_status_df = (
                    scan_problem_pods(
                        api_client
                    )
                )

            except Exception:
                pass


            st.rerun()


    # ========================================================
    # DOWNLOAD EXCEL
    # ========================================================

    st.divider()

    excel_buffer = io.BytesIO()


    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:

        filtered_df.to_excel(
            writer,
            index=False,
            sheet_name="Container Status",
        )


    st.download_button(
        "⬇️ Download Container Status Excel",
        data=excel_buffer.getvalue(),
        file_name="container_status.xlsx",
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )